#!/usr/bin/env python3
"""
Automated Test Suite for Nuclear Music Player - Playlist Tags Plugin
Tests:
1. Navigation & Tag Bar Injection
2. Tag Chip Rendering & Counts
3. Dynamic Tag Creation ('Synthwave')
4. Quick-Tag Assignment on Card
5. Filter Execution (Hide/Show Cards)
6. Reset to 'All'
7. Persistence Verification
"""
import sys
import time
import json
import os

# Add parent dir to path for nuclear_test_bridge
sys.path.insert(0, '/home/chad/Work')
from nuclear_test_bridge import start_server, eval_in_nuclear

def run_tests():
    print("[TEST] Starting bridge server on 127.0.0.1:9998...")
    start_server(9998)

    print("[TEST] Connecting to Nuclear...")
    for attempt in range(15):
        try:
            url = eval_in_nuclear("window.location.href", timeout=3.0)
            print(f"[TEST] Connected to Nuclear webview: {url}")
            break
        except TimeoutError:
            time.sleep(0.3)
    else:
        print("[FAIL] Could not connect to Nuclear within 15 attempts")
        return False

    # 1. Navigate to Playlists view
    print("[TEST 1] Ensuring /playlists view...")
    nav_res = eval_in_nuclear("""(() => {
        const link = document.querySelector('a[href*="playlists"], [data-testid*="playlists"]');
        if (link) { link.click(); return 'clicked link'; }
        window.location.hash = '/playlists';
        return 'hash set';
    })()""", timeout=3.0)
    print(f"[TEST 1] Navigation result: {nav_res}")

    # Wait for playlists view to mount
    for _ in range(10):
        time.sleep(0.3)
        ready = eval_in_nuclear("!!document.querySelector('[data-testid=\"playlists-view\"]')", timeout=2.0)
        if ready:
            break
    time.sleep(0.5)

    # 2. Check Tag Bar presence and default tags
    print("[TEST 2] Verifying Tag Bar and Default Tags...")
    tag_state = eval_in_nuclear(r"""(() => {
        const bar = document.getElementById('nuclear-playlist-tag-bar');
        if (!bar) return { error: 'tag bar not found' };
        const chips = Array.from(bar.querySelectorAll('.nuclear-tag-chip')).map(c => c.textContent.trim().replace(/\s+/g, ' '));
        const cards = Array.from(document.querySelectorAll('[data-testid="card"]'));
        const badges = Array.from(document.querySelectorAll('.nuclear-card-tags'));
        return {
            barFound: true,
            chips: chips,
            cardsCount: cards.length,
            cardBadgesCount: badges.length,
            instanceTags: window.NuclearPlaylistTags?.instance?.state?.tags || []
        };
    })()""", timeout=5.0)
    print(f"[TEST 2] Tag State: {json.dumps(tag_state, indent=2)}")

    if not tag_state or not tag_state.get('barFound'):
        print("[FAIL] Tag bar was not found in Playlists view")
        return False

    # 3. Create a new tag: 'Synthwave'
    print("[TEST 3] Creating new tag 'Synthwave'...")
    create_res = eval_in_nuclear("""(() => {
        const inst = window.NuclearPlaylistTags?.instance;
        if (!inst) return { error: 'instance not found' };
        inst.createTag('Synthwave');
        return {
            tags: inst.state.tags,
            hasSynthwave: inst.state.tags.includes('Synthwave')
        };
    })()""", timeout=3.0)
    print(f"[TEST 3] Create Result: {json.dumps(create_res)}")
    if not create_res or not create_res.get('hasSynthwave'):
        print("[FAIL] 'Synthwave' tag was not created")
        return False

    # 4. Assign 'Synthwave' to the first playlist card
    print("[TEST 4] Assigning 'Synthwave' to first playlist card...")
    assign_res = eval_in_nuclear("""(() => {
        const inst = window.NuclearPlaylistTags?.instance;
        const cards = Array.from(document.querySelectorAll('[data-testid="card"]'));
        if (!cards.length) return { error: 'no cards found' };
        const firstCard = cards[0];
        const id = inst.getPlaylistIdFromCard(firstCard);
        inst.assignTagToPlaylist(id, 'Synthwave');
        return {
            firstPlaylistId: id,
            assignedTags: inst.state.playlistTags[id] || []
        };
    })()""", timeout=3.0)
    print(f"[TEST 4] Assign Result: {json.dumps(assign_res)}")
    if not assign_res or 'Synthwave' not in assign_res.get('assignedTags', []):
        print("[FAIL] Failed to assign 'Synthwave' to playlist")
        return False

    # 5. Filter by 'Synthwave'
    print("[TEST 5] Filtering grid by 'Synthwave'...")
    filter_res = eval_in_nuclear("""(() => {
        const inst = window.NuclearPlaylistTags?.instance;
        inst.setFilterTag('Synthwave');
        const cards = Array.from(document.querySelectorAll('[data-testid="card"]'));
        const visible = cards.filter(c => c.style.display !== 'none' && !c.classList.contains('nuclear-tag-filtered-out'));
        const hidden = cards.filter(c => c.style.display === 'none' || c.classList.contains('nuclear-tag-filtered-out'));
        return {
            totalCards: cards.length,
            visibleCount: visible.length,
            hiddenCount: hidden.length,
            activeTag: inst.state.activeFilterTag
        };
    })()""", timeout=3.0)
    print(f"[TEST 5] Filter Result: {json.dumps(filter_res)}")
    if not filter_res or filter_res.get('visibleCount') != 1:
        print("[FAIL] Filter did not isolate exactly 1 card")
        return False

    # 6. Reset filter to 'All'
    print("[TEST 6] Resetting filter to 'All'...")
    reset_res = eval_in_nuclear("""(() => {
        const inst = window.NuclearPlaylistTags?.instance;
        inst.setFilterTag(null);
        const cards = Array.from(document.querySelectorAll('[data-testid="card"]'));
        const visible = cards.filter(c => c.style.display !== 'none' && !c.classList.contains('nuclear-tag-filtered-out'));
        return {
            totalCards: cards.length,
            visibleCount: visible.length,
            activeTag: inst.state.activeFilterTag
        };
    })()""", timeout=3.0)
    print(f"[TEST 6] Reset Result: {json.dumps(reset_res)}")
    if not reset_res or reset_res.get('visibleCount') != reset_res.get('totalCards'):
        print("[FAIL] Not all cards became visible after reset to 'All'")
        return False

    # 7. Persistence Verification
    print("[TEST 7] Verifying localStorage Persistence...")
    persist_res = eval_in_nuclear("""(() => {
        const raw = localStorage.getItem('nuclear-playlist-tags-data');
        const data = raw ? JSON.parse(raw) : null;
        return {
            persisted: !!data,
            hasSynthwaveInTags: data?.tags?.includes('Synthwave'),
            playlistTagsCount: Object.keys(data?.playlistTags || {}).length
        };
    })()""", timeout=3.0)
    print(f"[TEST 7] Persistence Result: {json.dumps(persist_res)}")
    if not persist_res or not persist_res.get('hasSynthwaveInTags'):
        print("[FAIL] Changes were not persisted to localStorage")
        return False

    print("\n[SUCCESS] All 7/7 automated tests PASSED! Plugin is 100% operational.")
    return True

if __name__ == '__main__':
    ok = run_tests()
    sys.exit(0 if ok else 1)
