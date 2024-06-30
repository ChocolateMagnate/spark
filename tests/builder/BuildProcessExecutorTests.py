import psutil

from spark.builder import BuildProcessExecutor


def test_pings():
    with BuildProcessExecutor(3) as executor:
        # We use the ping command because it's one of few cross-platform CLI commands.
        for command in [["ping", "-c", "3", "www.cloudflare.com"]] * 3:
            executor.submit(command)
        assert not executor.is_work_complete()
        for pid, code in executor.as_completed():
            assert code == 0


def test_is_work_completed():
    with BuildProcessExecutor(3) as executor:
        for command in [["ping", "-c", "3", "www.cloudflare.com"]] * 3:
            executor.submit(command)
        assert not executor.is_work_complete()
        for pid, code in executor.as_completed():
            assert code == 0
    assert executor.is_work_complete()


def test_progress():
    with BuildProcessExecutor(3) as executor:
        for command in [["ping", "-c", "3", "www.cloudflare.com"]] * 3:
            executor.submit(command)
        counter, total = executor.progress()
        assert total == 3
        assert counter == 0
        for _ in executor.as_completed():
            pass

        counter += 3
        updated_counter, total = executor.progress()
        assert updated_counter == counter
        assert total == 3


def test_empty_work():
    with BuildProcessExecutor(3) as executor:
        for pid, code in executor.as_completed():
            assert code is None


def test_process_is_reaped():
    with BuildProcessExecutor(3) as executor:
        for command in [["ping", "-c", "3", "www.cloudflare.com"]] * 3:
            executor.submit(command)
        for pid, code in executor.as_completed():
            assert not psutil.pid_exists(pid)


def test_implicit_build_start():
    with BuildProcessExecutor(3) as executor:
        for command in [["ping", "-c", "3", "www.cloudflare.com"]] * 3:
            executor.submit(command)
    current, total = executor.progress()
    assert current == total
    assert executor.is_work_complete()
