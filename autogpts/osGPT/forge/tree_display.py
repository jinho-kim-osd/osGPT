from typing import List, Optional, Union, Dict
import textwrap


class TreeNode:
    """
    Represents a node in a tree structure, containing content, metadata, and children nodes.
    """

    def __init__(self, content: str, metadata: Optional[Dict] = None):
        """
        Initializes a new TreeNode.

        :param content: The content of the node.
        :param metadata: Optional metadata associated with the node.
        """
        self.content = content
        self.metadata = metadata or {}
        self.children = []

    def add_child(self, child: "TreeNode"):
        """
        Adds a child node to this node.

        :param child: The child TreeNode to add.
        """
        self.children.append(child)


class TreeStructureDisplay:
    """
    Handles the display of a tree structure with formatted text indentation.
    """

    def __init__(self, indent_step: int = 4, line_width: int = 120):
        """
        Initializes the display settings for the tree structure.

        :param indent_step: The number of spaces for each level of indentation.
        :param line_width: The maximum width of a line of text before wrapping.
        """
        self.indent_step = indent_step
        self.line_width = line_width
        self.root = TreeNode("Root")

    def add_node(self, content: str, parent: Optional[TreeNode] = None, metadata: Optional[Dict] = None) -> TreeNode:
        """
        Adds a new node to the tree.

        :param content: The content of the node.
        :param parent: The parent node to add the new node to. If None, adds to the root.
        :param metadata: Optional metadata to associate with the node.
        :return: The created TreeNode.
        """
        node = TreeNode(content, metadata)
        (parent or self.root).add_child(node)
        return node

    def add_nodes_from_list(self, nodes: List[Union[str, TreeNode]], parent: Optional[TreeNode] = None):
        """
        Adds multiple nodes to the tree from a list.

        :param nodes: A list of TreeNode objects or strings. If strings, new nodes with those contents are created.
        :param parent: The parent node to add the new nodes to. If None, adds to the root.
        """
        for node in nodes:
            if isinstance(node, str):
                self.add_node(node, parent)
            elif isinstance(node, TreeNode):
                (parent or self.root).add_child(node)

    def _display(self, node: TreeNode, indent_level: int) -> List[str]:
        """
        Recursive helper function to generate the display lines for the tree.

        :param node: The current node being processed.
        :param indent_level: The current level of indentation.
        :return: A list of strings representing the lines of the display.
        """
        indent = " " * self.indent_step * indent_level
        content = textwrap.fill(node.content, width=self.line_width - len(indent), subsequent_indent=indent)
        lines = [f"{indent}{content}"]

        for child in node.children:
            lines.extend(self._display(child, indent_level + 1))

        return lines

    def display(self) -> str:
        """
        Generates the string representation of the tree structure.

        :return: A string representing the tree structure.
        """
        return "\n".join(self._display(self.root, -1)[1:])
