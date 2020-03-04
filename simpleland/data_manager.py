


class SnapshotManager:

    def __init__(self, log_size):
        self.log_size = log_size
        self.snapshot_log = [None for i in range(log_size)]
        self.snapshot_ids = [None for i in range(log_size)]
        self.snapshot_counter = 0

    def add_snapshot(self,snapshot_id, snapshot):
        self.snapshot_log[self.snapshot_counter % self.log_size] = snapshot
        self.snapshot_ids[self.snapshot_counter % self.log_size] = snapshot_id
        self.snapshot_counter +=1

    def _get_snapshot_idxs(self, tick_time_ms):
        idx_lookup = {v:i for i,v in enumerate(self.snapshot_ids)}
        lst = sorted([i for i in self.snapshot_ids if i is not None])
        next_idx = None
        previous_idx = None
        for i,v in enumerate(lst):
            if v >= tick_time_ms:
                next_idx = v
                if i > 0:
                    previous_idx = lst[i-1]
                break
        return idx_lookup.get(previous_idx,None), idx_lookup.get(next_idx,None)
    
    def get_snapshot_pair_by_id(self, tick_time_ms):
        prev_idx, next_idx = self._get_snapshot_idxs(tick_time_ms)
        next_snap = None if next_idx is None else self.snapshot_log[next_idx]
        prev_snap = None if prev_idx is None else self.snapshot_log[prev_idx]
        return prev_snap, next_snap

    def get_latest_snapshot(self):
        max_snapshot_id = None
        max_idx = None
        for idx,snapshot_id in enumerate(self.snapshot_ids):
            if snapshot_id is None:
                continue
            if max_snapshot_id is None or max_snapshot_id < snapshot_id:
                max_snapshot_id = snapshot_id
                max_idx = idx
        if max_snapshot_id is None:
            return None, None
        else:
            return (max_snapshot_id, self.snapshot_log[max_idx])


