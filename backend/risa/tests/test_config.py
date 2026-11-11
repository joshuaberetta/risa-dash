def test_map_fonts_come_from_settings(client, settings):
    assert client.get("/api/config").json()["fonts"] == {"regular": ["Noto Sans Regular"], "bold": ["Noto Sans Bold"]}
    # As on a kobo-in-a-box, whose tile server has Protomaps' fonts
    settings.MAP_FONT_BOLD = ["Noto Sans Medium"]
    assert client.get("/api/config").json()["fonts"]["bold"] == ["Noto Sans Medium"]
