import os
import setuptools

short_description = 'LaunchPanel is a simple interface designed to expose LaunchPad Actions to the user in an intuitive way.'
if os.path.exists('README.md'):
    with open('README.md', 'r') as fh:
        long_description = fh.read()

else:
    long_description = short_description

setuptools.setup(
    name='launchpanel',
    version='3.0.1',
    author='Mike Malinowski',
    author_email='mike.malinowski@outlook.com',
    description=short_description,
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mikemalinowski/launchpad',
    packages=setuptools.find_packages(),
    classifiers=[
        'Programming Language :: Python',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    package_data={
        '': ['_resources/*.png', '_resources/*.ui', '_resources/*.qss'],
    },
    install_requires=['qtility', 'scribble', 'factories', 'launchpad'],
    keywords="launch launchpad pad action actions launchpanel panel",
)
