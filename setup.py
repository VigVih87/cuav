from distutils.core import setup, Extension
import numpy as np
import platform

if platform.system() == 'Windows':
    jpegturbo_libpath = "c:\libjpeg-turbo-gcc\lib"
    jpegturbo_incpath = "c:\libjpeg-turbo-gcc\include"
    extra_compile_args=["-std=gnu99", "-O3"]
else:
    jpegturbo_libpath = "/opt/libjpeg-turbo/lib"
    jpegturbo_incpath = "/opt/libjpeg-turbo/include"
    if platform.machine().find('arm') != -1:
        extra_compile_args=["-std=gnu99", "-O3", "-mfpu=neon"]
    else:
        extra_compile_args=["-std=gnu99", "-O3"]
    

 
scanner = Extension('cuav.image.scanner',
                    sources = ['image/scanner.c'],
                    libraries = ['turbojpeg'],
                    library_dirs = [jpegturbo_libpath],
                    extra_compile_args=extra_compile_args)
 
setup (name = 'cuav',
       version = '1.0.0',
       description = 'CanberraUAV UAV code',
       url = 'https://github.com/CanberraUAV/cuav',
       author = 'CanberraUAV',
       author_email = 'andrew-cuav@tridgell.net',
       include_dirs = [np.get_include(),
                       jpegturbo_incpath],
       package_dir = { '' : '..' },
       packages = ['cuav', 'cuav.lib', 'cuav.image', 'cuav.camera', 'cuav.uav'],
       scripts = [ 'tools/geosearch.py', 'tools/geotag.py',
                   'tools/cuav_lens.py', 'tools/agl_mission.py',
                   'tests/cuav_benchmark.py' ],
       ext_modules = [scanner])