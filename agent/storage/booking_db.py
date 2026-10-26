"""
Read/Write Separated Database Engine for MantaBooking.
Implements CQRS (Command Query Responsibility Segregation) & Master-Replica architecture:
- Primary Write Node: SQLite WAL persistent database for ACID write transactions.
- Read Replica Pool: In-process, load-balanced read caches with indexed lookups.
- Replication: Replicas pull from the master's LSN-ordered replication log before serving reads,
  so every process (e.g. each gunicorn worker) converges on the same state.
- BookingDatabaseProxy: Dict-compatible proxy for backwards compatibility.

Every booking belongs to a user (`user_id`). Read APIs take a `user_id` and only return that
user's records; pass `user_id=None` only for internal/admin use.
"""

import os
import json
import time
import sqlite3
import threading
from itertools import cycle
from typing import Dict, Any, List, Optional, Iterator, Tuple, Set
from collections.abc import MutableMapping


# Directory for persistent master storage (override with DATA_DIR, e.g. a mounted disk in production)
DATA_DIR = os.path.abspath(
    os.getenv("DATA_DIR") or os.path.join(os.path.dirname(__file__), "..", "..", "data")
)
os.makedirs(DATA_DIR, exist_ok=True)
MASTER_DB_PATH = os.path.join(DATA_DIR, "bookings_master.db")


def connect_sqlite(db_path: str = MASTER_DB_PATH) -> sqlite3.Connection:
    """Opens a WAL-mode SQLite connection usable across threads."""
    conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30.0)
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    conn.row_factory = sqlite3.Row
    return conn


class PrimaryWriteDatabase:
    """
    Primary Master Database (Command Store).
    Dedicated strictly to WRITE operations (INSERT, UPDATE, DELETE).
    Ensures ACID compliance, persistent storage via SQLite WAL, and maintains an LSN replication log.
    """

    def __init__(self, db_path: str = MASTER_DB_PATH):
        self.db_path = db_path
        self.lock = threading.RLock()
        self.write_count = 0
        self.last_write_at: Optional[str] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        return connect_sqlite(self.db_path)

    def _init_db(self):
        with self.lock:
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bookings (
                        booking_id TEXT PRIMARY KEY,
                        internal_ref TEXT,
                        official_pnr TEXT,
                        category TEXT,
                        origin TEXT,
                        destination TEXT,
                        date TEXT,
                        passengers INTEGER,
                        passenger_names TEXT,
                        ticket_class TEXT,
                        total_cost_usd TEXT,
                        platform TEXT,
                        status TEXT,
                        user_id TEXT,
                        booked_at TEXT,
                        raw_json TEXT NOT NULL,
                        version INTEGER DEFAULT 1,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS replication_log (
                        lsn INTEGER PRIMARY KEY AUTOINCREMENT,
                        action TEXT NOT NULL,
                        booking_id TEXT NOT NULL,
                        payload TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_pnr ON bookings(official_pnr);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_ref ON bookings(internal_ref);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_cat ON bookings(category);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_bookings_user ON bookings(user_id);")
                conn.commit()
            finally:
                conn.close()

    def write(self, record: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
        """
        Executes a write transaction on the Primary Master database.
        Returns (lsn, record).
        """
        with self.lock:
            booking_id = (record.get("booking_id") or record.get("internal_ref") or "BKG-UNKNOWN").strip().upper()
            internal_ref = (record.get("internal_ref") or booking_id).strip().upper()
            official_pnr = (record.get("official_pnr") or "").strip().upper()
            category = record.get("category", "flight")
            origin = record.get("origin", "N/A")
            destination = record.get("destination", "N/A")
            travel_date = record.get("date", "N/A")
            passengers = int(record.get("passengers", 1))
            names = record.get("passenger_names") or []
            names_json = json.dumps(names)
            ticket_class = record.get("ticket_class", "Economy")
            total_cost = record.get("total_cost_usd", "$0.00")
            platform = record.get("platform", "Direct")
            status = record.get("status", "CONFIRMED")
            user_id = record.get("user_id", "")
            booked_at = record.get("booked_at") or time.strftime("%Y-%m-%d %H:%M:%S")

            clean_record = dict(record)
            clean_record["booking_id"] = booking_id
            clean_record["internal_ref"] = internal_ref
            clean_record["official_pnr"] = official_pnr
            clean_record["user_id"] = user_id
            clean_record["booked_at"] = booked_at
            raw_json = json.dumps(clean_record)

            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO bookings (
                        booking_id, internal_ref, official_pnr, category, origin,
                        destination, date, passengers, passenger_names, ticket_class,
                        total_cost_usd, platform, status, user_id, booked_at, raw_json, version, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(booking_id) DO UPDATE SET
                        internal_ref = excluded.internal_ref,
                        official_pnr = excluded.official_pnr,
                        category = excluded.category,
                        origin = excluded.origin,
                        destination = excluded.destination,
                        date = excluded.date,
                        passengers = excluded.passengers,
                        passenger_names = excluded.passenger_names,
                        ticket_class = excluded.ticket_class,
                        total_cost_usd = excluded.total_cost_usd,
                        platform = excluded.platform,
                        status = excluded.status,
                        user_id = excluded.user_id,
                        raw_json = excluded.raw_json,
                        version = version + 1,
                        updated_at = CURRENT_TIMESTAMP;
                """, (
                    booking_id, internal_ref, official_pnr, category, origin,
                    destination, travel_date, passengers, names_json, ticket_class,
                    total_cost, platform, status, user_id, booked_at, raw_json
                ))

                cursor.execute("""
                    INSERT INTO replication_log (action, booking_id, payload)
                    VALUES ('UPSERT', ?, ?);
                """, (booking_id, raw_json))
                lsn = cursor.lastrowid or 0
                conn.commit()

                self.write_count += 1
                self.last_write_at = time.strftime("%Y-%m-%d %H:%M:%S")
                return lsn, clean_record
            finally:
                conn.close()

    def delete(self, booking_id: str) -> int:
        """Executes a DELETE transaction and logs each removed booking to the replication log."""
        with self.lock:
            clean_id = booking_id.strip().upper()
            conn = self._get_connection()
            try:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT booking_id FROM bookings WHERE booking_id = ? OR internal_ref = ?;",
                    (clean_id, clean_id),
                )
                matched_ids = [row["booking_id"] for row in cursor.fetchall()]
                lsn = 0
                for matched_id in matched_ids:
                    cursor.execute("DELETE FROM bookings WHERE booking_id = ?;", (matched_id,))
                    cursor.execute("""
                        INSERT INTO replication_log (action, booking_id, payload)
                        VALUES ('DELETE', ?, '{}');
                    """, (matched_id,))
                    lsn = cursor.lastrowid or lsn
                conn.commit()
                if matched_ids:
                    self.write_count += 1
                    self.last_write_at = time.strftime("%Y-%m-%d %H:%M:%S")
                return lsn
            finally:
                conn.close()

    def get_current_lsn(self) -> int:
        """Returns the latest Log Sequence Number."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COALESCE(MAX(lsn), 0) FROM replication_log;")
            row = cursor.fetchone()
            return row[0] if row else 0
        finally:
            conn.close()

    def read_log_since(self, lsn: int) -> List[Tuple[int, str, str, Dict[str, Any]]]:
        """Returns replication events after `lsn`, in order: (lsn, action, booking_id, record)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT lsn, action, booking_id, payload FROM replication_log WHERE lsn > ? ORDER BY lsn ASC;",
                (lsn,),
            )
            return [
                (row["lsn"], row["action"], row["booking_id"], json.loads(row["payload"] or "{}"))
                for row in cursor.fetchall()
            ]
        finally:
            conn.close()

    def read_snapshot(self) -> Tuple[int, List[Dict[str, Any]]]:
        """Reads all records plus the LSN they reflect, in one consistent read (used for replica warm-up)."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("BEGIN;")
            cursor.execute("SELECT COALESCE(MAX(lsn), 0) FROM replication_log;")
            lsn = cursor.fetchone()[0]
            cursor.execute("SELECT raw_json FROM bookings ORDER BY updated_at ASC;")
            records = [json.loads(r["raw_json"]) for r in cursor.fetchall()]
            cursor.execute("COMMIT;")
            return lsn, records
        finally:
            conn.close()


class ReadReplicaDatabase:
    """
    Read Replica Node (Query Store).
    Dedicated strictly to READ operations (SELECT, LOOKUP, SEARCH, FILTER).
    Keeps indexed in-memory read structures and tracks replica metrics and latency.
    """

    def __init__(self, replica_id: str, replica_name: str, region: str = "local"):
        self.replica_id = replica_id
        self.replica_name = replica_name
        self.region = region
        self.lock = threading.RLock()
        self.applied_lsn = 0
        self.read_count = 0
        self.last_sync_at: Optional[str] = None
        self.last_read_at: Optional[str] = None
        self.avg_read_latency_ms: float = 0.05

        # Canonical storage: booking_id -> record
        self._records: Dict[str, Dict[str, Any]] = {}
        # Indexed lookups: key (booking_id, internal_ref, official_pnr) -> booking_ids.
        # A PNR can map to several bookings (different users may register the same PNR).
        self._index: Dict[str, Set[str]] = {}

    @staticmethod
    def _keys_for(booking_id: str, record: Dict[str, Any]) -> List[str]:
        keys = [booking_id]
        for field in ("internal_ref", "official_pnr"):
            value = record.get(field)
            if value:
                keys.append(str(value).strip().upper())
        return keys

    def _unindex(self, booking_id: str):
        rec = self._records.pop(booking_id, None)
        if not rec:
            return
        for key in self._keys_for(booking_id, rec):
            ids = self._index.get(key)
            if ids:
                ids.discard(booking_id)
                if not ids:
                    del self._index[key]

    def apply_replication(self, lsn: int, action: str, booking_id: str, record_data: Dict[str, Any]):
        """Applies a write event from the Primary Master's replication stream (idempotent, in LSN order)."""
        with self.lock:
            if lsn <= self.applied_lsn:
                return
            canonical_id = booking_id.strip().upper()
            self._unindex(canonical_id)

            if action in ("UPSERT", "INSERT", "UPDATE"):
                self._records[canonical_id] = record_data
                for key in self._keys_for(canonical_id, record_data):
                    self._index.setdefault(key, set()).add(canonical_id)

            self.applied_lsn = lsn
            self.last_sync_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def load_snapshot(self, lsn: int, records: List[Dict[str, Any]]):
        """Replaces replica state with a snapshot taken at `lsn`."""
        with self.lock:
            self._records.clear()
            self._index.clear()
            for rec in records:
                b_id = str(rec.get("booking_id") or rec.get("internal_ref") or "UNKNOWN").strip().upper()
                self._records[b_id] = rec
                for key in self._keys_for(b_id, rec):
                    self._index.setdefault(key, set()).add(b_id)
            self.applied_lsn = lsn
            self.last_sync_at = time.strftime("%Y-%m-%d %H:%M:%S")

    def _track_read(self, start_t: float):
        self.read_count += 1
        self.last_read_at = time.strftime("%Y-%m-%d %H:%M:%S")
        elapsed_ms = (time.perf_counter() - start_t) * 1000.0
        self.avg_read_latency_ms = round((self.avg_read_latency_ms * 0.9) + (elapsed_ms * 0.1), 3)

    @staticmethod
    def _visible(record: Dict[str, Any], user_id: Optional[str]) -> bool:
        return user_id is None or record.get("user_id") == user_id

    def get(self, key: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Reads a booking by primary ID, internal reference, or official carrier PNR."""
        with self.lock:
            start_t = time.perf_counter()
            clean_k = key.strip().upper()
            record = None
            for b_id in sorted(self._index.get(clean_k, ())):
                candidate = self._records.get(b_id)
                if candidate and self._visible(candidate, user_id):
                    record = candidate
                    break
            self._track_read(start_t)
            return dict(record) if record else None

    def list_all(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Reads all active booking records visible to `user_id`."""
        with self.lock:
            start_t = time.perf_counter()
            results = [dict(r) for r in self._records.values() if self._visible(r, user_id)]
            self._track_read(start_t)
            return results

    def find_by_pnr(self, pnr: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Specific read query targeting carrier PNR or session reference."""
        return self.get(pnr, user_id=user_id)

    def search(self, query: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search bookings matching query string."""
        with self.lock:
            start_t = time.perf_counter()
            q = query.strip().lower()
            matches = []
            for r in self._records.values():
                if not self._visible(r, user_id):
                    continue
                haystack = f"{r.get('booking_id','')} {r.get('internal_ref','')} {r.get('official_pnr','')} {r.get('origin','')} {r.get('destination','')} {r.get('category','')}".lower()
                if q in haystack:
                    matches.append(dict(r))
            self._track_read(start_t)
            return matches

    def count(self, user_id: Optional[str] = None) -> int:
        with self.lock:
            if user_id is None:
                return len(self._records)
            return sum(1 for r in self._records.values() if r.get("user_id") == user_id)


class ReadReplicaPool:
    """
    Manages a pool of Read Replicas.
    Provides round-robin query load-balancing and pulls replication events from the master log.
    """

    def __init__(self, replicas: List[ReadReplicaDatabase]):
        if not replicas:
            raise ValueError("ReadReplicaPool requires at least one ReadReplicaDatabase instance.")
        self.replicas = replicas
        self._selector = cycle(self.replicas)
        self.lock = threading.Lock()

    def get_replica(self) -> ReadReplicaDatabase:
        """Returns the next replica using Round-Robin load balancing."""
        with self.lock:
            return next(self._selector)

    def sync_replica(self, replica: ReadReplicaDatabase, primary: PrimaryWriteDatabase):
        """Catches a replica up with the master's replication log (picks up writes from other processes)."""
        with replica.lock:
            for lsn, action, booking_id, record in primary.read_log_since(replica.applied_lsn):
                replica.apply_replication(lsn, action, booking_id, record)

    def sync_all(self, primary: PrimaryWriteDatabase):
        for replica in self.replicas:
            self.sync_replica(replica, primary)

    def get_stats(self, master_lsn: int) -> List[Dict[str, Any]]:
        stats = []
        for r in self.replicas:
            lag = max(0, master_lsn - r.applied_lsn)
            stats.append({
                "replica_id": r.replica_id,
                "replica_name": r.replica_name,
                "region": r.region,
                "mode": "READ_ONLY",
                "status": "HEALTHY" if lag == 0 else "SYNCING",
                "applied_lsn": r.applied_lsn,
                "replication_lag_records": lag,
                "total_read_queries": r.read_count,
                "records_indexed": r.count(),
                "avg_latency_ms": r.avg_read_latency_ms,
                "last_sync_at": r.last_sync_at,
                "last_read_at": r.last_read_at,
            })
        return stats


class ReadWriteBookingManager:
    """
    CQRS / Read-Write Separation Orchestrator for MantaBooking.
    Coordinates the Primary Master Write Database and the Read Replica Pool.
    """

    def __init__(self, db_path: str = MASTER_DB_PATH):
        self.primary_db = PrimaryWriteDatabase(db_path=db_path)

        # Initialize Read Replica Pool (two in-process read caches)
        replica_1 = ReadReplicaDatabase(
            replica_id="replica-reader-01",
            replica_name="Read-Replica-1 (Primary Query Engine)",
            region="cluster-node-a"
        )
        replica_2 = ReadReplicaDatabase(
            replica_id="replica-reader-02",
            replica_name="Read-Replica-2 (Analytics & PNR Lookup Engine)",
            region="cluster-node-b"
        )
        self.replica_pool = ReadReplicaPool([replica_1, replica_2])

        # Warm-up / Initial state synchronization from Primary to Replicas
        self._warmup_replicas()

    def _warmup_replicas(self):
        """Loads a consistent snapshot of the Master into every Read Replica on startup."""
        lsn, records = self.primary_db.read_snapshot()
        for replica in self.replica_pool.replicas:
            replica.load_snapshot(lsn, records)

    def _read_replica(self) -> ReadReplicaDatabase:
        """Picks a replica and brings it up to date with the master before it serves a read."""
        replica = self.replica_pool.get_replica()
        self.replica_pool.sync_replica(replica, self.primary_db)
        return replica

    # ==========================================
    # WRITE / COMMAND APIs (Route to Primary DB)
    # ==========================================

    def save_booking(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        WRITE OPERATION:
        Persists booking strictly to Primary Master SQLite with WAL mode,
        then replicates to all Read Replicas.
        """
        _, clean_record = self.primary_db.write(record)
        self.replica_pool.sync_all(self.primary_db)
        return clean_record

    def delete_booking(self, booking_id: str) -> bool:
        """
        WRITE OPERATION:
        Deletes booking strictly on Primary Master SQLite, then replicates deletion.
        """
        self.primary_db.delete(booking_id)
        self.replica_pool.sync_all(self.primary_db)
        return True

    # ==========================================
    # READ / QUERY APIs (Route to Read Replicas)
    # ==========================================

    def get_booking(self, key: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        READ OPERATION:
        Routes read query to a load-balanced Read Replica.
        """
        return self._read_replica().get(key, user_id=user_id)

    def list_bookings(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        READ OPERATION:
        Routes list query to a load-balanced Read Replica.
        """
        return self._read_replica().list_all(user_id=user_id)

    def search_pnr(self, pnr: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        READ OPERATION:
        Routes PNR status inquiry to a load-balanced Read Replica.
        """
        return self._read_replica().find_by_pnr(pnr, user_id=user_id)

    def count(self, user_id: Optional[str] = None) -> int:
        """
        READ OPERATION:
        Returns active bookings count from a Read Replica.
        """
        return self._read_replica().count(user_id=user_id)

    # ==========================================
    # METRICS & OBSERVABILITY
    # ==========================================

    def get_metrics(self) -> Dict[str, Any]:
        """Returns real-time diagnostics of the Read/Write Separation architecture."""
        master_lsn = self.primary_db.get_current_lsn()
        replica_stats = self.replica_pool.get_stats(master_lsn)
        total_reads = sum(r["total_read_queries"] for r in replica_stats)
        total_writes = self.primary_db.write_count

        ratio = f"{round(total_reads / max(1, total_writes), 2)}:1" if total_writes > 0 else f"{total_reads}:0"

        return {
            "status": "OPERATIONAL",
            "architecture": "Read-Write Separation (Master-Replica CQRS)",
            "primary_master": {
                "name": "Master-Primary-DB",
                "type": "SQLite WAL Persistent Database",
                "mode": "WRITE_ONLY (Commands & Mutations)",
                "storage_file": os.path.basename(self.primary_db.db_path),
                "current_lsn": master_lsn,
                "total_writes": total_writes,
                "last_write_at": self.primary_db.last_write_at,
                "status": "ONLINE"
            },
            "read_replicas_pool": {
                "count": len(self.replica_pool.replicas),
                "load_balancing": "Round-Robin",
                "total_reads_served": total_reads,
                "read_write_ratio": ratio,
                "replicas": replica_stats
            },
            "performance": {
                "avg_query_latency_ms": round(sum(r["avg_latency_ms"] for r in replica_stats) / max(1, len(replica_stats)), 3),
                "active_connections": len(self.replica_pool.replicas) + 1,
                "thread_safety": "Multi-Threaded Reentrant Mutex + WAL Isolation"
            }
        }


class BookingDatabaseProxy(MutableMapping):
    """
    Dict-compatible proxy providing transparent Read/Write Separation:
    - Writes (`proxy[key] = val`) automatically route to Primary Master SQLite.
    - Reads (`proxy.get(key)`, `proxy[key]`, `values()`) automatically route to Read Replicas.
    Not user-scoped: internal/admin use only. Request handlers should call the manager with a user_id.
    """

    def __init__(self, manager: ReadWriteBookingManager):
        self.manager = manager

    def __setitem__(self, key: str, value: Any):
        """WRITE: Routes mutation strictly to Primary Master DB."""
        if isinstance(value, dict):
            rec = dict(value)
            if "booking_id" not in rec:
                rec["booking_id"] = str(key)
            self.manager.save_booking(rec)
        else:
            raise TypeError("Booking record must be a dictionary.")

    def __getitem__(self, key: str) -> Dict[str, Any]:
        """READ: Routes lookup strictly to Read Replica Pool."""
        record = self.manager.get_booking(str(key))
        if record is None:
            raise KeyError(key)
        return record

    def __delitem__(self, key: str):
        """WRITE: Routes deletion strictly to Primary Master DB."""
        self.manager.delete_booking(str(key))

    def __iter__(self) -> Iterator[str]:
        """READ: Iterates over booking IDs from Read Replica."""
        for b in self.manager.list_bookings():
            yield b.get("booking_id") or b.get("internal_ref") or ""

    def __len__(self) -> int:
        """READ: Returns count from Read Replica."""
        return self.manager.count()

    def get(self, key: str, default: Any = None) -> Any:
        """READ: Routes .get() call strictly to Read Replica Pool."""
        record = self.manager.get_booking(str(key))
        return record if record is not None else default

    def values(self) -> List[Dict[str, Any]]:
        """READ: Routes .values() call strictly to Read Replica Pool."""
        return self.manager.list_bookings()

    def items(self) -> List[Tuple[str, Dict[str, Any]]]:
        """READ: Routes .items() call strictly to Read Replica Pool."""
        bookings = self.manager.list_bookings()
        return [(b.get("booking_id") or b.get("internal_ref") or "", b) for b in bookings]

    def keys(self) -> List[str]:
        """READ: Routes .keys() call strictly to Read Replica Pool."""
        return [b.get("booking_id") or b.get("internal_ref") or "" for b in self.manager.list_bookings()]

    def __contains__(self, key: object) -> bool:
        """READ: Checks existence via Read Replica Pool."""
        if not isinstance(key, str):
            return False
        return self.manager.get_booking(key) is not None

    def get_metrics(self) -> Dict[str, Any]:
        """Observability helper returning DB metrics."""
        return self.manager.get_metrics()


# Global Singleton Manager and Dict Proxy
booking_db_manager = ReadWriteBookingManager()
BOOKING_DATABASE = BookingDatabaseProxy(booking_db_manager)
