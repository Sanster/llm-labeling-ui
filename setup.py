import os

import setuptools
from pathlib import Path

web_files = Path("llm_labeling_ui/out/").glob("**/*")
web_files = [str(it).replace("llm_labeling_ui/", "") for it in web_files]

CURRENT_DIR = Path(os.path.abspath(os.path.dirname(__file__)))
with open(CURRENT_DIR / "README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()


def load_requirements():
    requirements_file_name = "requirements.txt"
    requires = []
    with open(requirements_file_name) as f:
        for line in f:
            if line:
                requires.append(line.strip())
    return requires


setuptools.setup(
    name="llm-labeling-ui",
    version="0.5.0",
    author="PanicByte",
    author_email="cwq1913@gmail.com",
    description="LLM Labeling UI is an open source project for large language model data labeling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Sanster/llm-labeling-ui",
    packages=setuptools.find_packages("./"),
    package_data={"llm_labeling_ui": web_files},
    install_requires=load_requirements(),
    python_requires=">=3.7",
    entry_points={"console_scripts": ["llm-labeling-ui=llm_labeling_ui:entry_point"]},
    classifiers=[
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
)
