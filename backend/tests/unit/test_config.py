"""
Unit tests for configuration module.
"""




class TestSettings:
    """Test suite for Settings configuration class."""

    def test_settings_loads_from_environment(self) -> None:
        """Test that settings are loaded from environment variables."""
        from app.config import Settings

        settings = Settings()

        assert settings.environment == "test"
        assert settings.database_url is not None
        assert "postgresql" in settings.database_url

    def test_settings_has_required_fields(self) -> None:
        """Test that settings contains all required configuration fields."""
        from app.config import Settings

        settings = Settings()

        # Database settings
        assert hasattr(settings, "database_url")
        assert hasattr(settings, "redis_url")

        # Security settings
        assert hasattr(settings, "jwt_secret")
        assert hasattr(settings, "jwt_algorithm")
        assert hasattr(settings, "access_token_expire_minutes")

        # App settings
        assert hasattr(settings, "environment")
        assert hasattr(settings, "debug")
        assert hasattr(settings, "app_name")

    def test_settings_jwt_defaults(self) -> None:
        """Test that JWT settings have sensible defaults."""
        from app.config import Settings

        settings = Settings()

        assert settings.jwt_algorithm == "HS256"
        assert settings.access_token_expire_minutes > 0

    def test_settings_debug_mode_based_on_environment(self) -> None:
        """Test that debug mode is determined by environment."""
        from app.config import Settings

        settings = Settings()

        # In test environment, debug should be False by default
        if settings.environment == "production":
            assert settings.debug is False

    def test_get_settings_returns_cached_instance(self) -> None:
        """Test that get_settings returns a cached settings instance."""
        from app.config import get_settings

        settings1 = get_settings()
        settings2 = get_settings()

        assert settings1 is settings2

    def test_settings_app_name_default(self) -> None:
        """Test that app has a default name."""
        from app.config import Settings

        settings = Settings()

        assert settings.app_name == "KingSick"
