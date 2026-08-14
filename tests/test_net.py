import asyncio

from intern_engine import pipeline
from intern_engine.net import HostLimiter, _provider


class TestProviderFamily:
    def test_workday_hosts_share_one_family(self):
        assert _provider("acme.wd1.myworkdayjobs.com") == "workday"
        assert _provider("wd5.myworkdaysite.com") == "workday"

    def test_unknown_hosts_are_their_own_family(self):
        assert _provider("jobs.example.com") == "jobs.example.com"


class TestProviderCeiling:
    """The family ceiling has to bind on REQUESTS, not on boards.

    A slow board holds a slot far longer than a fast one, so Workday was
    reaching 31 of 32 simultaneous requests while Greenhouse averaged a
    fraction of one. The override exists to clip that peak.
    """

    def _peak(self, host, overrides, workers=24):
        limiter = HostLimiter(8, per_provider=32, overrides=overrides)
        live = 0
        peak = 0

        async def one():
            nonlocal live, peak
            permit = await limiter.acquire(host)
            async with permit:
                live += 1
                peak = max(peak, live)
                await asyncio.sleep(0.01)
                live -= 1

        asyncio.run(self._gather(one, workers))
        return peak

    @staticmethod
    async def _gather(factory, workers):
        await asyncio.gather(*(factory() for _ in range(workers)))

    def test_override_caps_the_family(self):
        # Distinct tenants, so the per-host limit of 8 is not what binds.
        assert self._peak("a.wd1.myworkdayjobs.com", {"workday": 4}) <= 4

    def test_without_an_override_the_general_limit_applies(self):
        peak = self._peak("a.wd1.myworkdayjobs.com", {})
        assert peak > 4  # free to use the wider per-provider allowance

    def test_an_override_does_not_leak_to_other_families(self):
        assert self._peak("boards.greenhouse.io", {"workday": 4}) > 4

    def test_per_host_still_binds_within_a_capped_family(self):
        # One host, so the tighter of (per_host=8, family=16) must win.
        assert self._peak("one.wd1.myworkdayjobs.com", {"workday": 16}) <= 8


class TestConfiguredCeilings:
    def test_workday_is_capped_below_the_global_gate(self):
        cap = pipeline.PROVIDER_CONCURRENCY["workday"]
        assert cap < pipeline.GLOBAL_CONCURRENCY
        # Still well above the per-host value: distinct tenants run in
        # parallel, which is the regression the old comment warns about.
        assert cap > pipeline.PER_HOST_CONCURRENCY
