from setuptools import setup, find_packages
import sys

if sys.version_info[:2] < (3, 5):
    raise RuntimeError("Python version >= 3.5 required.")


with open('README.md') as f:
    readme = f.read()

with open('LICENSE') as f:
    license = f.read()


setup(
    name='rnaseq_pipeline',
    version='0.0.1',
    description='python commandline tools for RNAseq Analysis',
    long_description=readme,
    author='illumination-k',
    author_email='illumination.k.27@gmail.com',
    install_requires=['pyyaml', 'pytest'],
    url='https://github.com/illumination-k/rnaseq-pipeline',
    license=license,
    packages=find_packages(exclude=('tests', 'docs')),
    entry_points={
        "console_scripts": [
            "rnaseq_pipeline=rnaseq_pipeline.__main__:main"
        ]
    },
    python_requires='>=3.5'
)