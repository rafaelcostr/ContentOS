"""ContentOS Plugin Marketplace — discovery, install, dynamic loading."""

from contentos_plugins_core.application.installer import PluginInstaller
from contentos_plugins_core.application.marketplace import PluginMarketplace, get_marketplace

__all__ = ["PluginInstaller", "PluginMarketplace", "get_marketplace"]
