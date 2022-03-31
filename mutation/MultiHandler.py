import threading, logging, time, random, os

# Global object we log to; the handler will work with any log message
#_L = logging.getLogger("demo")

# Create a special logger that logs to per-thread-name files
# I'm not confident the locking strategy here is correct, I think this is
# a global lock and it'd be OK to just have a per-thread or per-file lock.
class MultiHandler(logging.Handler):
    def __init__(self, dirname):
        super(MultiHandler, self).__init__()
        self.files = {}
        self.dirname = dirname
        if not os.access(dirname, os.W_OK):
            raise Exception("Directory %s not writeable" % dirname)

    def flush(self):
        self.acquire()
        try:
            for fp in self.files.values():
                fp.flush()
        finally:
            self.release()

    def _get_or_open(self, key):
        "Get the file pointer for the given key, or else open the file"
        self.acquire()
        try:
            if key in self.files: #self.files.has_key(key):
                return self.files[key]
            else:
                fp = open(os.path.join(self.dirname, "%s.log" % key), "a")
                self.files[key] = fp
                return fp
        finally:
            self.release()

    def emit(self, record):
        # No lock here; following code for StreamHandler and FileHandler
        try:
            fp = self._get_or_open(record.threadName)
            msg = self.format(record)
            fp.write('%s\n' % msg.encode("utf-8"))
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)