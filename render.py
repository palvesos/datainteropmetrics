import json
import os
from datetime import date

import pandas as pd
from jinja2 import Environment, FileSystemLoader


def load_data(data_dir: str = "data") -> dict:
    raise NotImplementedError


def compute_metrics(data: dict) -> dict:
    raise NotImplementedError


def render(
    metrics: dict,
    template_path: str = "templates/report.html.j2",
    output_path: str = "report.html",
) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    data = load_data()
    metrics = compute_metrics(data)
    render(metrics)
    print("Report written to report.html")
