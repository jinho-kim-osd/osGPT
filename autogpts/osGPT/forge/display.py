from typing import List, Optional, Union, Any
import textwrap


class TreeNode:
    def __init__(self, content: str, metadata: Optional[dict] = None):
        self.content = content
        self.metadata = metadata if metadata else {}
        self.children = []

    def add_child(self, child: "TreeNode"):
        self.children.append(child)


class TreeStructureDisplay:
    def __init__(self, indent_step=4, line_width=120):
        self.indent_step = indent_step
        self.line_width = line_width
        self.root = TreeNode("Root")

    def add_node(
        self,
        content: str,
        parent: Optional[TreeNode] = None,
        metadata: Optional[dict] = None,
    ):
        node = TreeNode(content, metadata)
        (parent if parent else self.root).add_child(node)
        return node

    def add_nodes_from_list(
        self, nodes: List[Union[str, TreeNode]], parent: Optional[TreeNode] = None
    ):
        parent_node = parent if parent else self.root
        for node in nodes:
            if isinstance(node, str):
                parent_node.add_child(TreeNode(node))
            elif isinstance(node, TreeNode):
                parent_node.add_child(node)

    def _display(self, node: TreeNode, indent_level: int) -> List[str]:
        lines = []
        indent = " " * self.indent_step * indent_level
        content = textwrap.fill(
            node.content, width=self.line_width - len(indent), subsequent_indent=indent
        )

        lines.append(f"{indent}{content}")

        for child in node.children:
            lines.extend(self._display(child, indent_level + 1))

        return lines

    def display(self) -> str:
        return "\n".join(self._display(self.root, -1)[1:])
