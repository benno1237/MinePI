from distutils.core import setup

setup(
    name = "MinePI",
    packages = ["MinePI"],
    version = "0.3.0",
    license = "MIT",
    description = "Minecraft utility library.",
    author = "benno1237, honigkuchen",
    author_email = "benno.kollreider@gmail.com",
    url = "https://github.com/benno1237/MinePI",
    download_url = "https://github.com/benno1237/MinePI/archive/refs/tags/0.3.0.tar.gz",
    keywords = ["Minecraft", "Skin", "Render", "Head", "UUID"],
    install_requires = [
        "aiohttp",
        "Pillow"
    ],
      classifiers=[
    'Development Status :: 3 - Alpha',     
    'Intended Audience :: Developers',      
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',  
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
    'Programming Language :: Python :: 3.10',
  ],
)
