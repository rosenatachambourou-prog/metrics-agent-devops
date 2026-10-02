def test_echec_volontaire():
    """Test volontairement faux : il doit faire échouer le pipeline.

    Sert à démontrer que la CI bloque le code cassé avant publication.
    Cette branche n'a pas vocation à être fusionnée.
    """
    assert 1 + 1 == 3
