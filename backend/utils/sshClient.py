import paramiko
import logging
import time


class SSHClientBase:
    def __init__(self, hostname: str, port: int, username: str, password: str, logger: logging.Logger):
        self.retry_delay = 3
        self.max_retries = 3
        self.logger = logger
        self.hostname = hostname
        self.port = port or 22
        self.username = username
        self.password = password
        self.ssh = self.connect_to_server()

    def connect_to_server(self) -> paramiko.SSHClient | None:
        if not all([self.hostname, self.username, self.password]):
            self.logger.error("Failed to check config: missing hostname, username, or password.")
            return None

        attempt = 0
        while attempt < self.max_retries:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.logger.info(
                    f"Attempting to connect to {self.hostname}:{self.port} as {self.username} (Attempt {attempt + 1})")
                try:
                    ssh.connect(self.hostname, self.port, self.username, self.password, timeout=120, banner_timeout=60)
                    self.logger.info("SSH connection established successfully.")
                    return ssh
                except paramiko.ssh_exception.SSHException as e:
                    self.logger.error(f"SSH connection failed: {e}")
                    self.close_ssh_connection()
                except Exception as e:
                    self.logger.error(f"Connection attempt failed: {e}")
                    self.close_ssh_connection()
                # finally:
                #     ssh.close()
            except Exception as e:
                self.logger.error(f"Unexpected error occurred: {e}")

            attempt += 1
            self.logger.info(f"Retrying in {self.retry_delay} seconds...")
            time.sleep(self.retry_delay)

        self.logger.error("Max retries reached. Failed to establish SSH connection.")
        return None

    def close_ssh_connection(self):
        if self.ssh and self.ssh.get_transport() and self.ssh.get_transport().is_active():
            self.ssh.close()
            self.logger.info("SSH connection closed.")

    def execute_command(self, command: str, check_output=True) -> tuple[bool, list | None]:
        if not self.ssh:
            self.logger.error("SSH connection is not established.")
            return False, None
        try:
            stdin, stdout, stderr = self.ssh.exec_command(command)
            exit_status = stdout.channel.recv_exit_status()
            if exit_status == 0:
                if check_output:
                    self.logger.info(f"Command executed successfully: {command}")
                output = [line.replace('\x08', '') for line in stdout.readlines()]
                return True, output
            else:
                if check_output:
                    self.logger.warning(
                        f"Command failed with exit status {exit_status}: Command: [{command}]: Error: {stderr.read()}")
                error_output = [line.replace('\x08', '') for line in stderr.readlines()]
                return False, error_output
        except Exception as e:
            self.logger.error(f"Failed to execute command: {e}")
            return False, None
