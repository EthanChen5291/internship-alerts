"""Conservative resume targeting without invented content."""

from pypdf import PdfReader

from intern_engine import resume_tailor


def _resume():
    return {
        "name": "Jordan Student",
        "contact": {"email": "jordan@example.com"},
        "skills": [{"category": "Languages", "items": ["Java", "Python", "C++"]}],
        "experience": [{
            "company": "Lab",
            "role": "Assistant",
            "start": "2025",
            "end": "Present",
            "bullets": [
                "Documented weekly research meetings.",
                "Built Python pipelines for machine learning datasets.",
            ],
        }],
        "projects": [{
            "name": "Web App",
            "bullets": ["Created a Java service.", "Trained a PyTorch image model."],
        }],
    }


def _job():
    return {
        "id": "job-1", "company": "Acme", "title": "Machine Learning Intern",
        "category": "Data & ML/AI", "skills": ["Python", "PyTorch"],
    }


def test_tailoring_only_reorders_existing_claims():
    before = _resume()
    after = resume_tailor.tailor(before, _job())
    assert after["experience"][0]["bullets"][0].startswith("Built Python")
    assert after["projects"][0]["bullets"][0].startswith("Trained a PyTorch")
    assert after["skills"][0]["items"][0] == "Python"
    assert sorted(after["experience"][0]["bullets"]) == sorted(
        before["experience"][0]["bullets"]
    )
    assert sorted(after["projects"][0]["bullets"]) == sorted(before["projects"][0]["bullets"])
    assert sorted(after["skills"][0]["items"]) == sorted(before["skills"][0]["items"])
    assert before["experience"][0]["bullets"][0].startswith("Documented")


def test_pdf_is_readable_and_contains_the_original_facts(tmp_path):
    output = tmp_path / "tailored.pdf"
    resume_tailor.write_pdf(resume_tailor.tailor(_resume(), _job()), output)
    reader = PdfReader(output)
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert len(reader.pages) == 1
    assert "Jordan Student" in text
    assert "Built Python pipelines" in text
    assert "Trained a PyTorch image model" in text
    assert "Acme" not in text  # target metadata is not printed on the resume
