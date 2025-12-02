"""Progress bar utilities."""

from tqdm import tqdm
from typing import Optional


class ProgressBar:
    """Wrapper for tqdm progress bars with consistent styling."""
    
    def __init__(
        self,
        total: int,
        desc: str,
        unit: str = "it",
        show_eta: bool = True
    ):
        """Initialize progress bar.
        
        Args:
            total: Total number of items
            desc: Description text
            unit: Unit name (e.g., 'file', 'chunk', 'batch')
            show_eta: Whether to show ETA
        """
        self.pbar = tqdm(
            total=total,
            desc=desc,
            unit=unit,
            bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]',
            ncols=100,
            colour='green'
        )
    
    def update(self, n: int = 1):
        """Update progress by n steps."""
        self.pbar.update(n)
    
    def set_postfix(self, **kwargs):
        """Set postfix text (e.g., cost estimate)."""
        self.pbar.set_postfix(**kwargs)
    
    def close(self, success_msg: Optional[str] = None):
        """Close progress bar and show completion message.
        
        Args:
            success_msg: Optional success message to display
        """
        self.pbar.close()
        if success_msg:
            print(f"✓ {success_msg}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.pbar.close()
