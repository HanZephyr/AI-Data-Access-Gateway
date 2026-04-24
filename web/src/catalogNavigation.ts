type TreeLikeNode = {
  key: string;
  children?: TreeLikeNode[];
};

export function findTreePathByKey(nodes: TreeLikeNode[], targetKey: string): string[] {
  /** Return the ancestor path for a target node key, including the target itself. */

  for (const node of nodes) {
    if (node.key === targetKey) {
      return [node.key];
    }
    const childPath = findTreePathByKey(node.children || [], targetKey);
    if (childPath.length) {
      return [node.key, ...childPath];
    }
  }
  return [];
}
