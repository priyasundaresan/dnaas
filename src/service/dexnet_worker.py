import multiprocessing, Queue
from threading import Thread
import os, shutil
import traceback

import consts

class _DexNetWorker(multiprocessing.Process):
    """ Dexnet worker process
    Used by DexNetWorker for multiprocessing/request based Dex-Net work
    """
    def __init__(self, process_name, gripper_dir):
        # Call super initializer
        super(_DexNetWorker, self).__init__()

        # Queues for interprocess management
        self._res_q    = multiprocessing.Queue()  # Result queue, for writing to dict-likes in main process
        self._req_q    = multiprocessing.Queue(1) # Request queue, getting requests from main process
        self._busy     = multiprocessing.Queue(1) # Busy flag, blocks requests
        self._call_ret = multiprocessing.Queue(1) # Return queue for function calls

        # Set attrs
        self._gripper_dir      = gripper_dir
        # Set name
        self.name = str(process_name)

        # Copy gripper to prevent collisions
        gripper_dir_this = os.path.join(gripper_dir, 'generic_{}'.format(self.name))
        gripper_dir_generic = os.path.join(gripper_dir, 'generic')
        shutil.rmtree(gripper_dir_this, ignore_errors=True)
        shutil.copytree(gripper_dir_generic, gripper_dir_this)

    def run(self):
        import dexnet_processor
        dexnet_processor.PROCESS_NAME = self.name
        # Setup persistent vars
        self._granular_progress = 0

        # Setup logging
        import logging
        logging.basicConfig(filename=os.path.join(consts.CACHE_DIR, 'logging_{}.log'.format(self.name)),
                            level=logging.INFO,
                            format='%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
                            datefmt='%m-%d %H:%M:%S',
                            filemode='a')

        try:
            while True:
                try:
                    req = self._req_q.get(block = True, timeout=10)
                    logging.debug("Request recieved")
                except Queue.Empty:
                    req = None

                if req is None:
                    pass
                elif req[0] == "TERM":
                    logging.debug("Termination request recieved, exiting")
                    return
                elif req[0] == "PROGRESS":
                    logging.debug("Progress request recieved, returning progress of {}".format(self._granular_progress))
                    self._call_ret.put(self._granular_progress)
                elif req[0] == "PROCESS":
                    self.busy = True
                    logging.debug("Job request recieved")
                    mesh_id = req[1][0]
                    args = req[1][1]
                    logging.info("Request for mesh of ID {} currently processing".format(mesh_id))
                    def executor_fn(*args):
                        try:
                            self.preprocess_mesh_internal(*args)
                        except MemoryError:
                            self.ret('progress', mesh_id, 'error')
                            self.ret('errors_handled', mesh_id, 'MemoryError')
                        except ValueError as e:
                            if 'array is too big' in e.message:
                                self.ret('progress', mesh_id, 'error')
                                self.ret('errors_handled', mesh_id, 'MemoryError')
                            else:
                                self.ret('progress', mesh_id, 'error')
                                self.ret('errors', mesh_id, traceback.format_exc())
                        except Exception:
                            self.ret('progress', mesh_id, 'error')
                            self.ret('errors', mesh_id, traceback.format_exc())
                        self.busy = False
                    executor_thread = Thread(target=executor_fn, args=(mesh_id,) + args)
                    executor_thread.start()
                else:
                    self.ret('errors', 'thread_'.format(self.name), "Invalid request {}".format(req[0]))

                if os.getppid() == 1:
                    logging.info("Parent process died, exiting")
                    logging.info("")
                    return
        except Exception:
            self.ret('errors', 'thread_'.format(self.name), traceback.format_exc())

    @property
    def busy(self):
        return self._busy.full()

    @busy.setter
    def busy(self, value):
        if value:
            if not self.busy:
                self._busy.put(1)
        else:
            if self.busy:
                self._busy.get()

    def ret(self, destination, mesh_id, result):
        self._res_q.put((destination,
                            (mesh_id,
                                result)
                        ))
    def req(self, todo, mesh_id, *args):
        self._req_q.put((todo,
                            (mesh_id,
                            args)
                        ), block=True)

    def preprocess_mesh_internal(self, mesh_id, gripper_params):
        import dexnet_processor
        def progress_reporter_big(message):
            self.ret('progress', mesh_id, message)
        def progress_reporter_small(percent):
            self._granular_progress = percent
        grasps, stbp_trans, stbp_grasp = dexnet_processor.preprocess_mesh(mesh_id, gripper_params, progress_reporter_big, progress_reporter_small)
        self.ret('filtered_grasps', mesh_id, grasps)
        self.ret('stbp_trans', mesh_id, stbp_trans)
        self.ret('stbp_grasp', mesh_id, stbp_grasp)
        self.ret('progress', mesh_id, 'done')

class DexNetWorker(object):
    """ Dex-net worker class
    """
    def __init__(self, process_name, gripper_dir=consts.GRIPPER_DIR):
        self.process_name     = str(process_name)
        self.gripper_dir      = gripper_dir

        self._worker = _DexNetWorker(self.process_name, self.gripper_dir)
        self._worker.daemon = True
        self._worker.start()

    @property
    def busy(self):
        return self._worker.busy

    @property
    def alive(self):
        return self._worker.is_alive()

    def restart(self):
        self._worker.req("TERM", None, None)
        self._worker.join(10)
        self._worker = _DexNetWorker(self.process_name, self.gripper_dir)
        self._worker.daemon = True
        self._worker.start()

    @property
    def progress(self):
        self._worker.req('PROGRESS', None)
        return self._worker._call_ret.get(block=True)

    def preprocess_mesh(self, mesh_id, gripper_params):
        self._worker.busy = True
        self._worker.req("PROCESS", mesh_id, gripper_params)

    @property
    def has_ret(self):
        return not self._worker._res_q.empty()

    @property
    def ret(self):
        return self._worker._res_q.get(block=False)
