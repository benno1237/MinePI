from distutils.core import setup

setup(
    name = "MinePI",
    packages = ["MinePI"],
    version = "0.1",
    license = "MIT",
    description = "Minecraft utility library.",
    author = "benno1237, honigkuchen",
    author_email = "",
    url = "",
    download_url = "",
    keywords = ["Minecraft", "Skin", "Render", "Head", "UUID"],
    install_requires = [
        "aiohttp",
        "Pillow"
    ],
      classifiers=[
    'Development Status :: 3 - Alpha',      # Chose either "3 - Alpha", "4 - Beta" or "5 - Production/Stable" as the current state of your package
    'Intended Audience :: Developers',      
    'Topic :: Software Development :: Build Tools',
    'License :: OSI Approved :: MIT License',  
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.7',
    'Programming Language :: Python :: 3.8',
    'Programming Language :: Python :: 3.9',
  ],
)