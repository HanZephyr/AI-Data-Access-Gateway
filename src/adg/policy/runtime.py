from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from adg.control_plane.models.governance import FieldPolicy, ResourcePolicy, ResourceTag
from adg.control_plane.models.resource import Resource


@dataclass(frozen=True)
class IdentityContext:
    tenant_id: str
    user_id: str
    roles: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str


class RuntimePolicyService:
    def __init__(self, session: Session) -> None:
        self._session = session

    def check_resource_access(
        self,
        *,
        identity: IdentityContext,
        resource: Resource,
        action: str,
    ) -> PolicyDecision:
        self._session.flush()
        policies = self._resource_policies(identity=identity, action=action)
        if not policies:
            return PolicyDecision(allowed=True, reason="no_policy")

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
        self._session.flush()
        policies = list(
            self._session.execute(
                select(FieldPolicy).where(
                    FieldPolicy.tenant_id == identity.tenant_id,
                    FieldPolicy.status == "active",
                    FieldPolicy.action == action,
                    FieldPolicy.resource_id == resource.id,
                    FieldPolicy.field_name == field_name,
                )
            ).scalars()
        )
        subject_policies = [policy for policy in policies if self._subject_matches(policy, identity)]
        if any(policy.effect == "deny" for policy in subject_policies):
            return PolicyDecision(allowed=False, reason="denied_by_policy")
        if any(policy.effect == "allow" for policy in subject_policies):
            return PolicyDecision(allowed=True, reason="allowed_by_policy")
        if policies:
            return PolicyDecision(allowed=False, reason="no_matching_allow")
        return PolicyDecision(allowed=True, reason="no_policy")

    def _resource_policies(
        self,
        *,
        identity: IdentityContext,
        action: str,
    ) -> list[ResourcePolicy]:
        return list(
            self._session.execute(
                select(ResourcePolicy).where(
                    ResourcePolicy.tenant_id == identity.tenant_id,
                    ResourcePolicy.status == "active",
                    ResourcePolicy.action == action,
                )
            ).scalars()
        )

    def _resource_policy_matches(self, policy: ResourcePolicy, resource: Resource) -> bool:
        if policy.resource_id is not None:
            return policy.resource_id == resource.id
        if policy.tag_id is not None:
            return (
                self._session.execute(
                    select(ResourceTag).where(
                        ResourceTag.tenant_id == resource.tenant_id,
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
        if policy.subject_type == "all":
            return True
        if policy.subject_type == "user":
            return policy.subject_id == identity.user_id
        if policy.subject_type == "role":
            return policy.subject_id in identity.roles
        if policy.subject_type == "group":
            return policy.subject_id in identity.groups
        return False
