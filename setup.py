from setuptools import setup, find_packages

setup(
    name="autoreply",
    version="0.1.5",
    packages=find_packages(),
    install_requires=[],
    author="Kirik",
    author_email="email@example.com",
    description="A simple Python library",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/wsc33332f/reply",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)