try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


install_requires = []

setup(name="ustack-etl",
      version="0.1.0",
      description="Framework for writing ETL processes from MongoDB to SQL",
      url="https://github.com/ustudio/ustack-etl",
      packages=["ustack_etl"],
      install_requires=install_requires)
