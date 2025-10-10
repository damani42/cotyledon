# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import typing
from unittest import TestCase
from unittest import mock

import pytest

import cotyledon


P = typing.ParamSpec("P")
R = typing.TypeVar("R")


class FakeService(cotyledon.Service):
    pass


class SomeTest(TestCase):
    def setUp(self) -> None:
        super().setUp()
        cotyledon.ServiceManager._process_runner_already_created = False

    def test_forking_slowdown(self) -> None:  # noqa: PLR6301
        sm = cotyledon.ServiceManager()
        sm.add(FakeService, workers=3)
        with mock.patch("time.sleep") as sleep:
            sm._slowdown_respawn_if_needed()
            sm._slowdown_respawn_if_needed()
            sm._slowdown_respawn_if_needed()
            # We simulatge 3 more spawn
            sm._slowdown_respawn_if_needed()
            sm._slowdown_respawn_if_needed()
            sm._slowdown_respawn_if_needed()
            assert len(sleep.mock_calls) == 6

    def test_invalid_service(self) -> None:
        sm = cotyledon.ServiceManager()

        self.assert_raises_msg(
            TypeError,
            "'service' must be a callable",
            sm.add,
            "foo",  # type: ignore[arg-type]
        )
        self.assert_raises_msg(
            ValueError,
            "'workers' must be an int >= 1, not: None (NoneType)",
            sm.add,
            FakeService,
            workers=None,  # type: ignore[arg-type]
        )
        self.assert_raises_msg(
            ValueError,
            "'workers' must be an int >= 1, not: -2 (int)",
            sm.add,
            FakeService,
            workers=-2,
        )

        oid = sm.add(FakeService, workers=3)
        self.assert_raises_msg(
            ValueError,
            "'workers' must be an int >= -2, not: -5 (int)",
            sm.reconfigure,
            oid,
            workers=-5,
        )
        self.assert_raises_msg(
            ValueError,
            "notexists service id doesn't exists",
            sm.reconfigure,
            "notexists",  # type: ignore[arg-type]
            workers=-1,
        )

    @staticmethod
    def assert_raises_msg(
        exc: type[Exception] | tuple[type[Exception], ...],
        msg: str,
        func: typing.Callable[P, R],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> None:
        with pytest.raises(exc) as exc_info:
            func(*args, **kwargs)
        assert msg == str(exc_info.value)


class TestOsloConfigGlue(TestCase):
    """Test oslo_config_glue functionality."""

    def setUp(self) -> None:
        super().setUp()
        cotyledon.ServiceManager._process_runner_already_created = False

    def test_setup_with_duplicate_options(self) -> None:
        """Test that setup handles duplicate options gracefully."""
        from oslo_config import cfg  # noqa: PLC0415

        from cotyledon import oslo_config_glue  # noqa: PLC0415

        # Create a config object
        conf = cfg.ConfigOpts()

        # Register options first time
        conf.register_opts(oslo_config_glue.service_opts)

        # Create a service manager
        sm = cotyledon.ServiceManager()

        # Setup should not raise DuplicateOptError
        # This simulates the scenario where options are already registered
        # (e.g., in test environments)
        oslo_config_glue.setup(sm, conf)

        # Check that all options exist
        for opt in oslo_config_glue.service_opts:
            conf._get(opt.name)

        # Verify that the service manager was configured
        self.assertEqual(sm._graceful_shutdown_timeout, 60)

    def test_setup_partial_registration(self) -> None:
        """Test that setup handles partial option registration correctly."""
        from oslo_config import cfg  # noqa: PLC0415

        from cotyledon import oslo_config_glue  # noqa: PLC0415

        conf = cfg.ConfigOpts()

        # Register only one option manually
        conf.register_opt(oslo_config_glue.service_opts[0])

        sm = cotyledon.ServiceManager()
        oslo_config_glue.setup(sm, conf)

        # All options should now be available
        for opt in oslo_config_glue.service_opts:
            conf._get(opt.name)
