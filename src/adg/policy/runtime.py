from dataclasses import dataclass, field

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.directory import Role, User, UserRole
from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag
from adg.control_plane.models.resource import Resource


@dataclass(frozen=True)
class IdentityContext:
    """Key-derived runtime identity used during policy and audit evaluation."""

    user_id: str | None
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    org_node_id: str | None = None

    @property
    def role_ids(self) -> list[str]:
        """Expose role identifiers with the new directory-driven naming."""

        return self.roles


def load_runtime_identity_for_user(
    session: Session,
    *,
    user_id: str | None,
) -> IdentityContext:
    """Load one runtime identity from a user binding on an authenticated API key."""

    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Runtime key must be bound to a user",
        )

    user = session.execute(
        select(User).where(User.id == user_id, User.status == "active")
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Runtime key user was not found",
        )

    role_ids = list(
        session.execute(
            select(Role.id)
            .join(UserRole, UserRole.role_id == Role.id)
            .where(
                UserRole.user_id == user.id,
                Role.status == "active",
            )
            .order_by(Role.id)
        ).scalars()
    )
    return IdentityContext(
        user_id=user.id,
        roles=role_ids,
        org_node_id=user.org_node_id,
    )


@dataclass(frozen=True)
class PolicyDecision:
    """Policy evaluation result with a stable machine-readable reason."""

    allowed: bool
    reason: str


class RuntimePolicyService:
    """Evaluates resource and field access against active governance policies."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def check_resource_access(
        self,
        *,
        identity: IdentityContext,
        resource: Resource,
        action: str,
    ) -> PolicyDecision:
        """Decide whether an identity may perform an action on a resource."""

        self._session.flush()
        policies = self._resource_policies(identity=identity, action=action)
        if not policies:
            return PolicyDecision(allowed=True, reason="no_policy")

        # Once policies exist for an action, at least one subject/resource match must allow it.
        matching = [
            policy
            for policy in policies
            if self._subject_matches(policy, identity)
            and self._resource_policy_matches(policy, resource)
        ]
        if any(policy.effect == "deny" for policy in matching):
            return PolicyDecision(allowed=False, reason="denied_by_policy")
        if any(policy.effect == "allow" for policy in matching):
            return PolicyDecision(allowed=True, reason="allowed_by_policy")
        return PolicyDecision(allowed=False, reason="no_matching_allow")

    def check_field_access(
        self,
        *,
        identity: IdentityContext,
        resource: Resource,
        field_name: str,
        action: str,
    ) -> PolicyDecision:
        """Decide field-level access after the parent resource has already been allowed."""

        self._session.flush()
        policies = list(
            self._session.execute(
                select(FieldPolicy).where(
                    FieldPolicy.status == "active",
                    FieldPolicy.action == action,
                    FieldPolicy.resource_id == resource.id,
                    FieldPolicy.field_name == field_name,
                )
            ).scalars()
        )
        subject_policies = [
            policy for policy in policies if self._subject_matches(policy, identity)
        ]
        if any(policy.effect == "deny" for policy in subject_policies):
            return PolicyDecision(allowed=False, reason="denied_by_policy")
        if any(policy.effect == "allow" for policy in subject_policies):
            return PolicyDecision(allowed=True, reason="allowed_by_policy")
        # Field policy presence switches the field from default-allow to require matching allow.
        if policies:
            return PolicyDecision(allowed=False, reason="no_matching_allow")
        return PolicyDecision(allowed=True, reason="no_policy")

    def _resource_policies(
        self,
        *,
        identity: IdentityContext,
        action: str,
    ) -> list[ResourcePolicy]:
        """Load active policies for one action before subject/resource filtering."""

        return list(
            self._session.execute(
                select(ResourcePolicy).where(
                    ResourcePolicy.status == "active",
                    ResourcePolicy.action == action,
                )
            ).scalars()
        )

    def _resource_policy_matches(self, policy: ResourcePolicy, resource: Resource) -> bool:
        """Match a policy to a resource directly, through a tag, or globally."""

        if policy.resource_id is not None:
            return policy.resource_id == resource.id
        if policy.tag_id is not None:
            return (
                self._session.execute(
                    select(ResourceTag).where(
                        ResourceTag.resource_id == resource.id,
                        ResourceTag.tag_id == policy.tag_id,
                    )
                ).scalar_one_or_none()
                is not None
            )
        return True

    def _subject_matches(
        self,
        policy: ResourcePolicy | FieldPolicy,
        identity: IdentityContext,
    ) -> bool:
        """Match a policy subject selector against the runtime identity."""

        if policy.subject_type == "all":
            return True
        if policy.subject_type == "user":
            return policy.subject_id == identity.user_id
        if policy.subject_type == "role":
            return policy.subject_id in identity.roles
        if policy.subject_type == "group":
            return policy.subject_id in identity.groups
        return False
