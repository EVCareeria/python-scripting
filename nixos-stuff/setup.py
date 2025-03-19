from setuptools import setup

setup(
    name='simple-calc',
    version='0.1',
    py_modules=['calculator'],
    entry_points={
        'console_scripts': [
            'simple-calc = calculator:calculator',  # Assumes you have a main() function in calculator.py
        ],
    },
)

