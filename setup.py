from setuptools import setup, find_packages

setup(
    name="orderflow",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "tabulate",  # For formatted table output
    ],
    entry_points={
        'console_scripts': [
            'orderflow=orderflow.main:main',
        ],
    },
)