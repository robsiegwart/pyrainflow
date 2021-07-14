from setuptools import setup

setup(
    name='pyrainflow',
    pymodules=['pyrainflow'],
    version='0.1.0',
    entry_points={
        'console_scripts': [
            'pyrainflow = pyrainflow.cli:cli'
        ]
    },
    install_requires=[
        'pandas',
        'matplotlib'
    ],
    package_data={'':['Sample data/*']}
)