import os
import shutil
import time

__lock_dir__ = "lock"
__version_dir__ = "versions"

class Lock():
    """
    Class for locking application.
    Implemment:
        - One global file lock for all installation directory, that make 
          possibility for save lock change during next actions processing.
          file: app.lock
        - Multi job application lock for running multiJob instance
          file: %mj_name%_app.lock
        - Installation lock for save installing set version of installation
          files: install.lock, __version_dir__/install.version
        - Data version for save copiing and deleting data accoding set
          version (jobs session). For opperation is used app.lock
          file: __version_dir__/%mj_name%_data.version
        - Library lock for save installing set library version
          files: lib.lock
    """
    def __init__(self, mj_name, path):
        """init"""
        self._mj_name = mj_name
        """Multijob name for unique jobs identification"""
        self._js_path = path
        if not os.path.isdir(path):
            os.makedirs(path)
        """Path to js directory"""
        self._lock_dir = os.path.join(path, __lock_dir__)
        """Path to lock application directory"""
        if not os.path.isdir(self._lock_dir):
            os.makedirs(self._lock_dir)
        self._version_dir = os.path.join(path, __version_dir__)
        """Path to version files"""
        
    def lock_app(self,  install_ver, data_ver,  res_dir):
        """
        Check if application with mj_name is not runnig
        and is installed right version of installation.
        
          - If other app with same name is running throw exception
          - If installation lock is set, wait for lock 300 second and if 
            another installation is not finished throw exception
          - If version of installation is different and other *_app.lock 
            is locked throw exception            
          - If version of installation is different and any *_app.lock 
            is not locked, install.lock is set and all js directory is 
            removed. Unlock install must be called after installation
          - If data version is diferent, remove multijob data dir
        return True if install lock is set
        """
        res = True
        if self._lock_file("app.lock"):
            if not self._lock_file(self._mj_name + "_app.lock", 0):
                self._unlock_file("app.lock")
                raise LockFileError("MuliJob application (" + self._mj_name + ") is running.")
            # first instance locked
            if not self._lock_file("install.lock", 0):
                self._unlock_file("app.lock")
                if not self._lock_file("install.lock", 300):
                    self._unlock_file(self._mj_name + "_app.lock")
                    raise LockFileError(" application (" + self._mj_name + ") is running.")                
                if not self._lock_file("app.lock"):
                    self._unlock_file(self._mj_name + "_app.lock")
                    self._unlock_file("install.lock")
                    raise LockFileError("Global lock can't be set.")
            installed_ver = self._read_version("install.version")                       
            if installed_ver is None or installed_ver !=  install_ver:
                if self._is_mj_lock_set():                    
                    self._unlock_file(self._mj_name + "_app.lock")
                    self._unlock_file("install.lock")
                    self._unlock_file("app.lock")                    
                    raise LockFileError("New version can't be installed, old application is running.")
                #delete app dir
                names = os.listdir( self._js_path)
                for name in names:
                    path = os.path.join(self._js_path,name)
                    if os.isdir(path) and name != self._lock_dir:
                        shutil.rmtree(path, ignore_errors=True)
            else:
                self._unlock_file("install.lock")
                res = False
            # installation ready
            dataed_ver = self._read_version(self._mj_name + "_data.version")
            if dataed_ver is None or dataed_ver != data_ver:
                if os.isdir(res_dir):
                    shutil.rmtree(res_dir, ignore_errors=True)            
            # data_ready            
        else:
            raise LockFileError("Global lock can't be set.")
        self._unlock_file("app.lock")
        return res
            
    def unlock_app(self):
        """Application with mj_name is stopping"""
        self._lock_file("app.lock")
        self._unlock_file(self._mj_name + "_app.lock")
        self._unlock_file("app.lock")                           
        
    def unlock_install(self):
        """Installation is finished"""
        self._lock_file("app.lock")
        self._unlock_file("install.lock")
        self._unlock_file("app.lock")                           
        
    def lock_lib(self, lib_dir):
        """
        Check if library lock is empty. If is, lib lock is set.
        
        return True if lib lock is set
        """
        res = True
        if self._lock_file("app.lock"):
            if self._lock_file("lib.lock", 300):
                if os.isdir(lib_dir):
                    names = os.listdir(self.lib_dir)
                    if len(names) == 0:
                        self._unlock_file("lib.lock")
                        res = False
                else:
                    self._unlock_file("lib.lock")
                    res = False
            else:                
                self._unlock_file("app.lock") 
                raise LockFileError("Library lock can't be set.")
        else:
            raise LockFileError("Global lock can't be set.")
        self._unlock_file("app.lock")
        return res 
        
    def unlock_lin(self):
        """Library is installed"""
        self._lock_file("app.lock")
        self._unlock_file("lib.lock")
        self._unlock_file("app.lock") 
 
    def _lock_file(self, file, timeout=120):
        """
        lock set file lock
        
        retun: True if lock is locked
        """
        sec = time.time() + timeout
        path = os.path.join(self._lock_dir, file)
        while sec < time.time():
            try:
                fd = os.open(path, os.O_CREAT|os.O_EXCL)
                os.close(fd)
                return True
            except OSError:
                time.sleep(5)
            except:
                return False
        return False
            
    def _unlock_file(self, file):
        """lock global lock"""
        path = os.path.join(self._lock_dir, file)
        os.remove(path)
        
    def _is_mj_lock_set(self):
        """return True if any multijob lock is set"""
        names = os.listdir(self._lock_dir)
        for name in names:
            if len(name)>9 and name[-9:] == "_app.lock":
                return True
        return False
        
    def _read_version(self, file):
        """Return version string or None if file is not exist"""
        path = os.path.join(self._version_dir, file)
        version = None
        try:
            with open(path, 'r') as f:
                version = f.readline()
            f.closed
        except:
            return None
        return version
        
class LockFileError(Exception):
    """Represents an error in lock file class"""

    def __init__(self, msg):
        super(LockFileError, self).__init__(msg)
