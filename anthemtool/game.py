from anthemtool.toc.layout import Layout


class FrostbiteGame:
    """
    Represents a Frostbite game instance.
    """

    def __init__(self, path: str) -> None:
        """
        Load the game data files from /Data and /Patch.
        """
        self.path = path

        # Initialize layouts
        self.layout_data = Layout(self, 'Data')
        self.layout_patch = Layout(self, 'Patch', parent=self.layout_data)
