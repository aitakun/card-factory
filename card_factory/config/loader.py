"""Configuration loader for card factory YAML files"""

import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional


class CardFactoryConfig:
    """Configuration class for card factory settings"""
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path
        self.template_pattern: Optional[str] = None
        self.template_default: str = "template/hardware.svg"
        self.filter_column: Optional[str] = None
        self.filter_contains: Optional[str] = None
        self.bindings: List[Dict[str, Any]] = []
        self.visibility: List[Dict[str, Any]] = []
        self.color_schemes: Dict[str, Any] = {}
        self.substitutions: Dict[str, str] = {}
        self.output_directory: str = "export"
        self.filename_pattern: str = "{name}.svg"
        self.preview_enabled: bool = False
        self.preview_width: int = 800
        self.spreadsheet_cleanup: bool = True
        
        if config_path:
            self.load(config_path)
    
    def load(self, config_path: str) -> None:
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if not config:
            raise ValueError(f"Empty configuration file: {config_path}")
        
        # Load template settings
        if 'template' in config:
            template_config = config['template']
            if isinstance(template_config, dict):
                self.template_pattern = template_config.get('pattern')
                self.template_default = template_config.get('default', self.template_default)
            elif isinstance(template_config, str):
                self.template_default = template_config
        
        # Load filter settings
        if 'filter' in config:
            filter_config = config['filter']
            if isinstance(filter_config, dict):
                self.filter_column = filter_config.get('column')
                self.filter_contains = filter_config.get('contains')
        
        # Load bindings
        if 'bindings' in config:
            self.bindings = config['bindings']
        
        # Load visibility settings
        if 'visibility' in config:
            self.visibility = config['visibility']
        
        # Load color schemes
        if 'color_schemes' in config:
            self.color_schemes = config['color_schemes']
        
        # Load substitutions
        if 'substitutions' in config:
            self.substitutions = config['substitutions']
        
        # Load output settings
        if 'output' in config:
            output_config = config['output']
            if isinstance(output_config, dict):
                self.output_directory = output_config.get('directory', self.output_directory)
                self.filename_pattern = output_config.get('filename_pattern', self.filename_pattern)
                preview_config = output_config.get('preview')
                if preview_config and isinstance(preview_config, dict):
                    self.preview_enabled = preview_config.get('enabled', self.preview_enabled)
                    self.preview_width = preview_config.get('width', self.preview_width)
            elif isinstance(output_config, str):
                self.output_directory = output_config
        
        # Load spreadsheet settings
        if 'spreadsheet' in config:
            spreadsheet_config = config['spreadsheet']
            if isinstance(spreadsheet_config, dict):
                self.spreadsheet_cleanup = spreadsheet_config.get('cleanup', self.spreadsheet_cleanup)
    
    def get_bindings(self) -> List[Dict[str, Any]]:
        """Get the list of bindings"""
        return self.bindings
    
    def get_visibility(self) -> List[Dict[str, Any]]:
        """Get the list of visibility conditions"""
        return self.visibility
    
    def get_color_schemes(self) -> Dict[str, Any]:
        """Get color schemes configuration"""
        return self.color_schemes
    
    def get_substitutions(self) -> Dict[str, str]:
        """Get string substitutions"""
        return self.substitutions
    
    def get_filter(self) -> tuple:
        """Get filter settings as (column, contains) tuple"""
        return (self.filter_column, self.filter_contains)
    
    def should_cleanup_spreadsheet(self) -> bool:
        """Check if downloaded spreadsheet file should be cleaned up after use"""
        return self.spreadsheet_cleanup
    
    def should_include_row(self, row: Dict[str, Any]) -> bool:
        """Check if a row should be included based on filter.
        
        Supports '|' operator for OR logic. For example:
        - filter_contains = "hardware|gene" matches if column contains "hardware" OR "gene"
        """
        if not self.filter_column or not self.filter_contains:
            return True
        
        value = str(row.get(self.filter_column, "")).lower()
        
        # Support | for OR logic
        if '|' in self.filter_contains:
            patterns = self.filter_contains.lower().split('|')
            return any(pattern in value for pattern in patterns)
        
        return self.filter_contains.lower() in value
