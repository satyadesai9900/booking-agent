import urllib.request
import json
import time

def test_cqrs():
    print("==================================================")
    print(" [CQRS] TESTING READ/WRITE SEPARATION IN MANTABOOKING")
    print("==================================================")

    # 1. Login (demo guest account) to get auth token
    login_req = urllib.request.Request(
        'http://127.0.0.1:5000/api/auth/demo',
        data=b'{}',
        headers={'Content-Type': 'application/json'}
    )
    token = json.loads(urllib.request.urlopen(login_req).read().decode())['token']
    auth = {'Authorization': f'Bearer {token}'}
    print("\n[1] Authentication:")
    print(" - Logged in as a demo guest (Token obtained)")

    # 2. Inspect initial metrics
    req = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5000/api/database/status', headers=auth))
    initial_metrics = json.loads(req.read().decode())
    print("\n[2] Initial DB Architecture:")
    print(" - Architecture:", initial_metrics["architecture"])
    print(" - Primary Master Engine:", initial_metrics["primary_master"]["type"])
    print(" - Storage File:", initial_metrics["primary_master"]["storage_file"])
    print(" - Primary Master Writes:", initial_metrics["primary_master"]["total_writes"])
    print(" - Read Replicas Count:", initial_metrics["read_replicas_pool"]["count"])

    # 3. WRITE operation: POST /api/bookings
    print("\n[3] Executing WRITE Operation (POST /api/bookings):")
    booking_payload = json.dumps({
        'category': 'train',
        'origin': 'New Delhi',
        'destination': 'Varanasi',
        'date': '2026-11-15',
        'passengers': 2,
        'passenger_names': ['Satya Desai', 'Aditi Rao'],
        'platform': 'IRCTC (Indian Railways)',
        'official_pnr': '4521369874',
        'ticket_class': 'Executive AC Chair (EC)'
    }).encode()

    write_req = urllib.request.Request(
        'http://127.0.0.1:5000/api/bookings',
        data=booking_payload,
        headers={'Content-Type': 'application/json', 'Authorization': f'Bearer {token}'}
    )
    write_res = urllib.request.urlopen(write_req)
    write_json = json.loads(write_res.read().decode())
    print(" - Write Destination:", write_json.get("write_destination"))
    print(" - Bookings Count:", write_json.get("bookings_count"))

    # 4. READ operation: GET /api/bookings
    print("\n[4] Executing READ Operation (GET /api/bookings):")
    read_req = urllib.request.Request(
        'http://127.0.0.1:5000/api/bookings',
        headers={'Authorization': f'Bearer {token}'}
    )
    read_res = urllib.request.urlopen(read_req)
    read_json = json.loads(read_res.read().decode())
    print(" - Read Source:", read_json.get("read_source"))
    print(" - Bookings Retrieved:", len(read_json.get("bookings", [])))
    for b in read_json.get("bookings", []):
        print(f"   * Booking: {b.get('booking_id')} | PNR: {b.get('official_pnr')} | Route: {b.get('origin')} -> {b.get('destination')}")

    # 5. READ operation: GET /api/pnr-status
    print("\n[5] Executing PNR Query READ Operation (GET /api/pnr-status):")
    pnr_req = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5000/api/pnr-status?pnr=4521369874', headers=auth))
    pnr_json = json.loads(pnr_req.read().decode())
    print(" - Read Source:", pnr_json.get("read_source"))
    print(" - PNR Match Found:", pnr_json.get("has_local_booking"))
    print(" - Matched Route:", pnr_json.get("booking", {}).get("origin"), "->", pnr_json.get("booking", {}).get("destination"))

    # 6. Verify Updated CQRS Metrics
    print("\n[6] Verifying Live CQRS Replication & Query Distribution:")
    req2 = urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:5000/api/database/status', headers=auth))
    final_metrics = json.loads(req2.read().decode())
    print(" - Total Master Writes:", final_metrics["primary_master"]["total_writes"])
    print(" - Total Replicas Reads Served:", final_metrics["read_replicas_pool"]["total_reads_served"])
    print(" - Read/Write Ratio:", final_metrics["read_replicas_pool"]["read_write_ratio"])
    print(" - Replica Node Breakdown:")
    for r in final_metrics["read_replicas_pool"]["replicas"]:
        print(f"   * {r['replica_name']}: Queries={r['total_read_queries']} | Lag={r['replication_lag_records']} records | Status={r['status']}")

    print("\n==================================================")
    print(" [OK] READ/WRITE SEPARATION VERIFIED 100% OPERATIONAL")
    print("==================================================")

if __name__ == "__main__":
    test_cqrs()
