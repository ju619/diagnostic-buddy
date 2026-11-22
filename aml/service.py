from .calibration import InvalidImage, coordinates, decode


def analyze(data, selection, analyzer, classify=False):
    if not isinstance(selection, dict) or set(selection) != {"bar", "cell"}:
        raise InvalidImage("Mark the scale bar and draw a box around one cell.")
    bar = coordinates(selection["bar"])
    cell = coordinates(selection["cell"])
    return analyzer.analyze_frame(decode(data), bar, cell, classify)

