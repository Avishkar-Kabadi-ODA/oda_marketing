from setuptools import find_packages, setup

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

from oda_marketing import __version__ as version

setup(
	name="oda_marketing",
	version=version,
	description="Agentic marketing operations platform for ODA",
	author="Optimum Data Analytics",
	author_email="info@optimumdataanalytics.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=[req for req in install_requires if req and not req.startswith("#")],
)
