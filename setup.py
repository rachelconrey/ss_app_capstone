from setuptools import setup, find_packages

setup(
    name="capstone_ss_app",
    version="0.1.0",
    description="Sports Source Application",
    author="Your Name",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[
        "shiny>=0.6.0",
        "pandas>=2.0.0",
        "sqlalchemy>=2.0.0",
        "python-dotenv>=1.0.0",
        "psycopg2-binary>=2.9.0",
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
    ],
    python_requires=">=3.8",
)