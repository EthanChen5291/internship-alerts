"""Connector parsing tests using mocked ATS responses (no network).

Each connector is fed a canned payload through a fake Net, so we verify the
schema-to-Job mapping for every source without hitting the internet.
"""

import asyncio

from intern_engine.connectors import (
    amazon,
    ashby,
    breezy,
    eightfold,
    greenhouse,
    lever,
    oracle,
    recruitee,
    rippling,
    smartrecruiters,
    workable,
    workday,
)
from intern_engine.models import Fetch


class FakeNet:
    """Stands in for net.Net: returns a preset payload for any request."""

    def __init__(self, payload):
        self.payload = payload
        self.urls = []

    async def get_json(self, url, **kwargs):
        self.urls.append(url)
        return self.payload

    async def post_json(self, url, **kwargs):
        self.urls.append(url)
        return self.payload


def _run(coro):
    """Run a connector and return its jobs.

    Connectors may return a bare list or a models.Fetch (jobs + completeness);
    these tests care about the parsing, so normalize to the job list. Tests that
    assert on completeness use `_fetch` instead.
    """
    return _fetch(coro).jobs


def _fetch(coro) -> Fetch:
    return Fetch.of(asyncio.run(coro))


def test_greenhouse():
    payload = {"jobs": [{
        "id": 42, "title": "Software Engineer Intern",
        "location": {"name": "New York, NY"}, "absolute_url": "https://gh/42",
        "first_published": "2026-06-01T08:00:00-04:00",
        "updated_at": "2026-06-15T00:00:00Z",
    }]}
    jobs = _run(greenhouse.fetch({"name": "Acme", "slug": "acme"}, FakeNet(payload)))
    assert len(jobs) == 1
    j = jobs[0]
    assert j.id == "greenhouse:acme:42"
    assert j.title == "Software Engineer Intern"
    assert j.location == "New York, NY"
    assert j.url == "https://gh/42"
    assert j.posted_at == "2026-06-01T08:00:00-04:00"  # true publish date, not updated_at


def test_lever():
    payload = [{
        "id": "abc", "text": "SWE Intern",
        "categories": {"location": "San Francisco"},
        "hostedUrl": "https://lever/abc", "createdAt": 1717200000000,
        "descriptionPlain": "Build things.",
        "additionalPlain": "We are unable to sponsor visas.",
        "salaryRange": {"min": 40000, "max": 60000, "currency": "USD", "interval": "per-year-salary"},
    }]
    jobs = _run(lever.fetch({"name": "Acme", "slug": "acme"}, FakeNet(payload)))
    assert jobs[0].id == "lever:acme:abc"
    assert jobs[0].location == "San Francisco"
    assert jobs[0].posted_at and jobs[0].posted_at.startswith("2024")
    assert "unable to sponsor" in jobs[0].description  # free text for the classifier
    assert jobs[0].salary == "40,000–60,000 USD/yr"


def test_ashby_skips_unlisted():
    payload = {"jobs": [
        {"title": "SWE Intern", "location": "SF", "jobUrl": "https://ashby/x/uuid1",
         "publishedAt": "2026-06-01T00:00:00Z", "isListed": True},
        {"title": "Hidden", "jobUrl": "https://ashby/x/uuid2", "isListed": False},
    ]}
    jobs = _run(ashby.fetch({"name": "Acme", "slug": "x"}, FakeNet(payload)))
    assert len(jobs) == 1
    assert jobs[0].id == "ashby:x:uuid1"
    assert jobs[0].posted_at == "2026-06-01T00:00:00Z"


def test_smartrecruiters():
    payload = {"content": [{
        "id": "p1", "name": "Data Science Intern",
        "location": {"city": "Austin", "region": "TX", "country": "us"},
        "releasedDate": "2026-06-10T00:00:00Z",
    }]}
    jobs = _run(smartrecruiters.fetch({"name": "Acme", "slug": "Acme"}, FakeNet(payload)))
    assert jobs[0].id == "smartrecruiters:Acme:p1"
    assert "United States" in jobs[0].location
    assert jobs[0].posted_at == "2026-06-10T00:00:00Z"


def test_amazon():
    payload = {"jobs": [{
        "title": "SDE Intern", "job_path": "/en/jobs/1/sde",
        "normalized_location": "Seattle, Washington, USA",
        "posted_date": "June 1, 2026", "id_icims": "1",
    }]}
    jobs = _run(amazon.fetch({"name": "Amazon", "slug": "amazon"}, FakeNet(payload)))
    assert jobs[0].url == "https://www.amazon.jobs/en/jobs/1/sde"
    assert jobs[0].posted_at.startswith("2026-06-01")


def test_rippling():
    payload = [{
        "uuid": "u1", "name": "Backend Intern",
        "workLocation": {"label": "Remote, US"}, "url": "https://ats.rippling.com/x/jobs/u1",
    }]
    jobs = _run(rippling.fetch({"name": "Acme", "slug": "x"}, FakeNet(payload)))
    assert jobs[0].id == "rippling:x:u1"
    assert jobs[0].location == "Remote, US"


def test_workday_relative_dates():
    payload = {"jobPostings": [
        {"title": "SWE Intern", "externalPath": "/job/1", "locationsText": "Austin, TX",
         "postedOn": "Posted 3 Days Ago"},
        {"title": "Old Intern", "externalPath": "/job/2", "locationsText": "NY",
         "postedOn": "Posted 30+ Days Ago"},
    ]}
    company = {"name": "Acme", "slug": "acme", "wd": "wd5", "site": "Careers"}
    net = FakeNet(payload)
    result = _fetch(workday.fetch(company, net))
    jobs = result.jobs
    assert jobs[0].posted_at is not None        # "3 Days Ago" resolves to a date
    assert jobs[1].posted_at is None            # "30+ Days Ago" is too vague
    assert jobs[0].url.endswith("/Careers/job/1")
    # Both searches ran to exhaustion, so this is the company's whole list.
    assert result.complete
    # The two search terms return the same postings here; identity is the job
    # id, so the overlap collapses instead of double-listing every role.
    assert len(jobs) == 2
    # 2 postings < page size -> one request per term, no useless pagination.
    assert len(net.urls) == 2
    assert net.urls[0] == "https://acme.wd5.myworkdayjobs.com/wday/cxs/acme/Careers/jobs"


def test_workday_path_style_host():
    payload = {"jobPostings": [
        {"title": "SWE Intern", "externalPath": "/job/1", "locationsText": "AZ"},
    ]}
    company = {"name": "Microchip", "slug": "microchiphr", "wd": "wd5",
               "site": "External", "host": "wd5.myworkdaysite.com"}
    net = FakeNet(payload)
    jobs = _run(workday.fetch(company, net))
    assert net.urls[0] == "https://wd5.myworkdaysite.com/wday/cxs/microchiphr/External/jobs"
    assert jobs[0].url == "https://wd5.myworkdaysite.com/recruiting/microchiphr/External/job/1"


def test_workable():
    payload = {"results": [{
        "title": "AI Inference Engineer Intern", "shortcode": "ABC123",
        "published": "2026-06-10T00:00:00Z", "remote": False,
        "location": {"country": "United States", "city": "Burlingame", "region": "California"},
    }], "nextPage": None}
    jobs = _run(workable.fetch({"name": "Quadric", "slug": "quadric"}, FakeNet(payload)))
    assert jobs[0].id == "workable:quadric:ABC123"
    assert jobs[0].url == "https://apply.workable.com/quadric/j/ABC123/"
    assert jobs[0].location == "Burlingame, California, United States"
    assert jobs[0].posted_at == "2026-06-10T00:00:00Z"


def test_breezy():
    payload = [{
        "id": "fa06", "name": "SWE Intern", "url": "https://acme.breezy.hr/p/fa06-swe",
        "published_date": "2026-06-15T16:41:15.395Z",
        "location": {"name": "Provo, UT"}, "salary": "$25/hr",
    }]
    jobs = _run(breezy.fetch({"name": "Acme", "slug": "acme"}, FakeNet(payload)))
    assert jobs[0].id == "breezy:acme:fa06"
    assert jobs[0].location == "Provo, UT"
    assert jobs[0].salary == "$25/hr"
    assert jobs[0].posted_at.startswith("2026-06-15")


class TestSnapshotCompleteness:
    """A capped response must say so, or the store closes live roles.

    Every source here caps its result count. A capped page is indistinguishable
    from "this company has no more roles" unless the connector reports it — and
    the store closes anything a complete fetch didn't return.
    """

    def test_full_page_with_more_pending_is_incomplete(self):
        # A full page and a server total far above it: the rest was cut off.
        posting = {"title": "SWE Intern", "externalPath": "/job/1",
                   "locationsText": "Austin, TX"}
        payload = {"total": 5000, "jobPostings": [posting] * 20}
        company = {"name": "Medtronic", "slug": "medtronic", "wd": "wd1",
                   "site": "MedtronicCareers"}
        result = _fetch(workday.fetch(company, FakeNet(payload)))
        assert result.complete is False

    def test_short_page_is_complete(self):
        payload = {"total": 1, "jobPostings": [
            {"title": "SWE Intern", "externalPath": "/job/1", "locationsText": "TX"},
        ]}
        company = {"name": "Acme", "slug": "acme", "wd": "wd5", "site": "Careers"}
        assert _fetch(workday.fetch(company, FakeNet(payload))).complete is True

    def test_amazon_reports_truncation(self):
        job = {"title": "SDE Intern", "job_path": "/en/jobs/1/sde",
               "normalized_location": "Seattle, WA", "id_icims": "1"}
        capped = {"hits": 9000, "jobs": [job] * 100}
        assert _fetch(amazon.fetch({}, FakeNet(capped))).complete is False
        whole = {"hits": 1, "jobs": [job]}
        assert _fetch(amazon.fetch({}, FakeNet(whole))).complete is True

    def test_smartrecruiters_reports_truncation(self):
        posting = {"id": "p1", "name": "Data Science Intern",
                   "location": {"city": "Austin", "region": "TX", "country": "us"}}
        company = {"name": "Acme", "slug": "Acme"}
        capped = {"totalFound": 900, "content": [posting] * 100}
        assert _fetch(smartrecruiters.fetch(company, FakeNet(capped))).complete is False
        whole = {"totalFound": 1, "content": [posting]}
        assert _fetch(smartrecruiters.fetch(company, FakeNet(whole))).complete is True

    def test_whole_board_connectors_are_complete_when_well_formed(self):
        # Greenhouse reads the entire board in one call — nothing to truncate.
        payload = {"jobs": [{"id": 1, "title": "SWE Intern",
                             "location": {"name": "NY"}, "absolute_url": "u"}]}
        result = _fetch(greenhouse.fetch({"name": "Acme", "slug": "acme"},
                                         FakeNet(payload)))
        assert result.complete is True

    def test_an_empty_board_is_still_complete(self):
        # A real board with zero openings must be able to close its old roles.
        result = _fetch(greenhouse.fetch({"name": "Acme", "slug": "acme"},
                                         FakeNet({"jobs": []})))
        assert result.jobs == []
        assert result.complete is True

    def test_malformed_200_is_not_an_empty_board(self):
        # The dangerous case: an API answering `{}` or an error object parses
        # fine and yields zero jobs, which is indistinguishable from "no
        # openings" — and would close EVERY role that employer has.
        company = {"name": "Acme", "slug": "acme"}
        for payload in ({}, {"error": "rate limited"}, {"jobs": None}, []):
            result = _fetch(greenhouse.fetch(company, FakeNet(payload)))
            assert result.jobs == []
            assert result.complete is False, payload

    def test_every_whole_board_connector_rejects_garbage(self):
        garbage = {"unexpected": "shape"}
        company = {"name": "Acme", "slug": "acme", "host": "h", "domain": "d"}
        for mod in (greenhouse, lever, ashby, breezy, recruitee, rippling):
            result = _fetch(mod.fetch(company, FakeNet(garbage)))
            assert result.complete is False, mod.__name__

    def test_eightfold_full_page_without_a_total_is_incomplete(self):
        # `int(data.get("count") or 0)` made a missing count read as 0, so
        # `start >= 0` was trivially true and a truncated page looked complete.
        position = {"id": 1, "name": "SWE Intern", "locations": ["NY"],
                    "t_create": 1782086400}
        company = {"name": "Netflix", "slug": "netflix", "ats": "eightfold",
                   "host": "explore.jobs.netflix.net", "domain": "netflix.com"}
        full = {"positions": [position] * 100}  # a full page, no count field
        assert _fetch(eightfold.fetch(company, FakeNet(full))).complete is False


def test_recruitee():
    payload = {"offers": [{
        "id": 99, "title": "Data Intern", "city": "Amsterdam", "country": "Netherlands",
        "careers_url": "https://acme.recruitee.com/o/data-intern",
        "created_at": "2026-06-01", "description": "<p>No visa sponsorship.</p>",
    }]}
    jobs = _run(recruitee.fetch({"name": "Acme", "slug": "acme"}, FakeNet(payload)))
    assert jobs[0].id == "recruitee:acme:99"
    assert jobs[0].location == "Amsterdam, Netherlands"
    assert "sponsorship" in jobs[0].description


def test_oracle():
    payload = {"items": [{"requisitionList": [
        {"Id": "9", "Title": "ML Intern", "PrimaryLocation": "Dearborn, MI",
         "PostedDate": "2026-06-05"},
    ]}]}
    company = {"name": "Ford", "slug": "ford", "host": "x.oraclecloud.com", "site": "CX_1"}
    jobs = _run(oracle.fetch(company, FakeNet(payload)))
    assert jobs[0].id == "oracle:ford:9"
    assert jobs[0].posted_at == "2026-06-05"


def test_eightfold():
    payload = {"count": 1, "positions": [{
        "id": 790316547536, "ats_job_id": "JR31938",
        "name": "AI/ML Scientist Intern, Fall 2026",
        "locations": ["Los Gatos,California,United States of America"],
        "location": "Los Gatos,California,United States of America",
        "t_create": 1782086400, "t_update": 1782090000,
        "canonicalPositionUrl": "https://explore.jobs.netflix.net/careers/job/790316547536",
        "job_description": "<p>Experience with Python and PyTorch. "
                           "Unable to sponsor visas for this role.</p>",
    }]}
    company = {"name": "Netflix", "slug": "netflix", "ats": "eightfold",
               "host": "explore.jobs.netflix.net", "domain": "netflix.com"}
    jobs = _run(eightfold.fetch(company, FakeNet(payload)))
    assert len(jobs) == 1
    j = jobs[0]
    assert j.id == "eightfold:netflix:790316547536"
    assert j.company == "Netflix"
    assert j.title == "AI/ML Scientist Intern, Fall 2026"
    assert j.location == "Los Gatos, California, United States of America"
    assert j.posted_at == "2026-06-22T00:00:00Z"
    assert j.url.endswith("/790316547536")
    assert "Python" in j.description and "sponsor" in j.description


def test_eightfold_no_positions():
    company = {"name": "Netflix", "slug": "netflix", "ats": "eightfold",
               "host": "explore.jobs.netflix.net", "domain": "netflix.com"}
    jobs = _run(eightfold.fetch(company, FakeNet({"count": 0, "positions": []})))
    assert jobs == []


class TestMalformedResponses:
    """A malformed HTTP 200 is not an empty board — for EVERY connector.

    Six whole-board connectors were fixed first; the five paginated ones still
    read `{}` as "short page, therefore exhausted" and reported complete, which
    lets one bad response close an entire employer's roles.
    """

    COMPANY = {"name": "Acme", "slug": "acme", "wd": "wd5", "site": "S",
               "host": "h.oraclecloud.com", "domain": "d"}
    MODULES = (greenhouse, lever, ashby, breezy, recruitee, rippling,
               amazon, eightfold, oracle, smartrecruiters, workable, workday)

    def test_no_connector_reports_complete_on_an_empty_object(self):
        for mod in self.MODULES:
            result = _fetch(mod.fetch(self.COMPANY, FakeNet({})))
            assert result.complete is False, mod.__name__

    def test_no_connector_reports_complete_on_an_error_payload(self):
        for mod in self.MODULES:
            result = _fetch(mod.fetch(self.COMPANY,
                                      FakeNet({"error": "rate limited"})))
            assert result.jobs == [], mod.__name__
            assert result.complete is False, mod.__name__


class TestAmazonLocation:
    """Amazon's search is worldwide, so the country half has to be right."""

    def _loc(self, **fields):
        return amazon._location(fields)

    def test_us_roles_expand_the_state(self):
        # normalized_location said "Westboro, Wisconsin"; city/state say MA.
        assert self._loc(city="Westboro", state="MA", country_code="US",
                         normalized_location="Westboro, Wisconsin, USA") == \
            "Westboro, Massachusetts, USA"

    def test_foreign_roles_are_named_not_state_coded(self):
        from intern_engine import filters
        # "Toronto, ON, CA" handed the region filter California; "Bangalore,
        # KA, IN" handed it Indiana. Both then passed as US.
        for fields, country in (
            (dict(city="Toronto", state="ON", country_code="CA"), "Canada"),
            (dict(city="Bangalore", state="KA", country_code="IN"), "India"),
            (dict(city="Munich", state="BY", country_code="DE"), "Germany"),
        ):
            loc = self._loc(**fields)
            assert loc.endswith(country), loc
            assert not filters.is_united_states(loc), loc

    def test_unknown_country_is_not_guessed_as_us(self):
        from intern_engine import filters
        loc = self._loc(city="Somewhere", state="ZZ", country_code="ZZ")
        assert not filters.is_united_states(loc), loc

    def test_missing_country_only_reads_us_for_a_real_state_code(self):
        from intern_engine import filters
        assert filters.is_united_states(self._loc(city="Austin", state="TX"))
        # "BC" is not a US state — don't silently default the country to US.
        assert not filters.is_united_states(self._loc(city="Vancouver", state="BC"))


class TestErrorEnvelopes:
    """An error wearing an empty board's clothes must not read as complete.

    `{"error": "rate limited", "jobs": []}` passed the earlier shape check —
    the container IS a list — and closed every role that employer had. Only a
    TRUTHY error disqualifies: Amazon ships `"error": null` on healthy pages.
    """

    COMPANY = {"name": "Acme", "slug": "acme", "wd": "wd5", "site": "S",
               "host": "h.oraclecloud.com", "domain": "d"}
    ENVELOPES = {
        greenhouse: {"error": "rate limited", "jobs": []},
        ashby: {"error": "rate limited", "jobs": []},
        recruitee: {"error": "x", "offers": []},
        workable: {"error": "x", "results": []},
        smartrecruiters: {"error": "x", "content": []},
        workday: {"error": "x", "jobPostings": []},
        eightfold: {"error": "x", "positions": []},
        amazon: {"error": "throttled", "jobs": [], "hits": 0},
        oracle: {"error": "x", "items": []},
    }

    def test_error_with_a_wellformed_empty_container_is_incomplete(self):
        for mod, payload in self.ENVELOPES.items():
            result = _fetch(mod.fetch(self.COMPANY, FakeNet(payload)))
            assert result.jobs == [], mod.__name__
            assert result.complete is False, mod.__name__

    def test_amazon_null_error_field_is_a_healthy_response(self):
        payload = {"error": None, "hits": 1, "jobs": [{
            "title": "SDE Intern", "job_path": "/j/1", "id_icims": "1",
            "city": "Seattle", "state": "WA", "country_code": "US",
        }]}
        result = _fetch(amazon.fetch({}, FakeNet(payload)))
        assert result.complete is True
        assert len(result.jobs) == 1

    def test_junk_list_members_poison_completeness(self):
        # `[{}]` parses as a list of dicts but yields id ":None" rows. Those
        # are dropped, and their presence means the listing can't be trusted
        # to close anything.
        result = _fetch(greenhouse.fetch({"name": "Acme", "slug": "acme"},
                                         FakeNet({"jobs": [{}]})))
        assert result.jobs == []
        assert result.complete is False
