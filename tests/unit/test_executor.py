import pytest
from server.core.executor import CommandResult, SystemCommandExecutor
from tests.mocks.executor import MockCommandExecutor


@pytest.mark.asyncio
async def test_system_executor_run_echo():
    executor = SystemCommandExecutor()
    res = await executor.run(["echo", "hello world"])
    assert res.returncode == 0
    assert res.stdout == "hello world"
    assert res.stderr == ""
    assert not res.timed_out


@pytest.mark.asyncio
async def test_system_executor_run_with_stdin():
    executor = SystemCommandExecutor()
    res = await executor.run_with_stdin(["cat"], stdin_data="line1\nline2\n")
    assert res.returncode == 0
    assert "line1\nline2" in res.stdout


@pytest.mark.asyncio
async def test_system_executor_command_not_found():
    executor = SystemCommandExecutor()
    res = await executor.run(["non_existent_binary_xyz_12345"])
    assert res.returncode == 127
    assert "Executable not found" in res.stderr


@pytest.mark.asyncio
async def test_system_executor_timeout():
    executor = SystemCommandExecutor()
    res = await executor.run(["sleep", "2"], timeout=0.1)
    assert res.timed_out
    assert res.returncode == -1
    assert "timed out" in res.stderr.lower()


def test_system_executor_run_sync():
    executor = SystemCommandExecutor()
    res = executor.run_sync(["echo", "sync test"])
    assert res.returncode == 0
    assert res.stdout == "sync test"


@pytest.mark.asyncio
async def test_mock_executor_matches():
    mock = MockCommandExecutor()
    mock.register(["uname", "-r"], CommandResult(0, "6.6.0-mock-linux", ""))
    mock.register_prefix(["ping", "-c"], CommandResult(0, "mock ping OK", ""))
    mock.set_default(CommandResult(1, "", "unknown command"))

    res1 = await mock.run(["uname", "-r"])
    assert res1.returncode == 0
    assert res1.stdout == "6.6.0-mock-linux"

    res2 = await mock.run(["ping", "-c", "3", "1.1.1.1"])
    assert res2.returncode == 0
    assert res2.stdout == "mock ping OK"

    res3 = await mock.run(["something", "else"])
    assert res3.returncode == 1
    assert res3.stderr == "unknown command"
