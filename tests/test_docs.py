from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_readme_keeps_the_proposal_honest():
    readme = (ROOT / "README.md").read_text()
    required = [
        "Status: proposal / early prototype.",
        "22-mile loop",
        "2.5 million annual visits (Atlanta Beltline, 2025)",
        "99.9%",
        "design target",
        "No station is deployed.",
        "no agreement with Atlanta Beltline, Inc.",
        "about 5",
        "Serenity Software Solutions LLC",
        "rodney.burns@s3-bi.tech",
        "s3-bi.tech",
        "Apache-2.0",
        "WeatherXM stations",
        "Streamr",
    ]
    for phrase in required:
        assert phrase in readme, phrase
    assert "millions of daily" not in readme.lower()
    assert "M1 in progress" in readme
    assert "has not been awarded" in readme
    assert "No Streamr stream has been created" in readme


def test_schema_creates_tables_and_does_not_seed_rows():
    schema = (ROOT / "db" / "schema.sql").read_text().lower()
    assert "create table if not exists stations" in schema
    assert "create table if not exists observations" in schema
    assert "create table if not exists air_quality_observations" in schema
    assert "create_hypertable" in schema
    assert "insert into" not in schema
    assert "cc by 4.0" in schema
    assert "weatherxm terms" in schema


def test_license_is_apache_2():
    license_text = (ROOT / "LICENSE").read_text()
    assert "Apache License" in license_text
    assert "Version 2.0, January 2004" in license_text


def test_milestones_match_the_draft_and_stay_unfinished():
    text = (ROOT / "docs" / "milestones.md").read_text()
    for token in ("M1", "M2", "M3", "M4", "Weeks 0–6", "Weeks 6–10", "Weeks 10–16", "Weeks 16–24"):
        assert token in text
    assert "Not started" in text
    assert "$10,000" in text
    assert "not an award" in text
