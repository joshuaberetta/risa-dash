from django.test import override_settings


def test_guide_is_served_from_the_built_frontend(client, tmp_path):
    (tmp_path / "guide").mkdir()
    (tmp_path / "guide" / "index.html").write_text("<h1>RISA Dashboard user guide</h1>")
    (tmp_path / "index.html").write_text("<div id=root></div>")
    with override_settings(FRONTEND_DIST=tmp_path):
        r = client.get("/guide")
        assert r.status_code == 301 and r["Location"] == "/guide/"
        r = client.get("/guide/")
        assert r.status_code == 200 and b"user guide" in r.content
        # Deeper paths are still the React app
        assert b"root" in client.get("/guide/elsewhere").content
