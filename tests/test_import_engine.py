def test_import():
    import spectrum_gse

    assert spectrum_gse.SpectrumGSE is not None
    assert spectrum_gse.SPECTRUM_GSE == "1.0.0"
