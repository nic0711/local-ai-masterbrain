# 5. Security Hardening

## Run as Non-root

```bash
sudo adduser --system --group --home /opt/appservice appservice
sudo usermod -aG docker appservice
sudo -u appservice python3 start_services.py --profile cpu --environment public
```

## Firewall: UFW + Docker Fix

UFW (Uncomplicated Firewall) is easy to configure, but **Docker bypasses it**. To secure exposed ports:

1. Enable UFW (for general traffic control):
   ```bash
   sudo ufw enable
   sudo ufw allow 22
   sudo ufw allow 80
   sudo ufw allow 443
   ```

2. Prevent Docker from bypassing firewall rules:
   ```bash
   sudo iptables -I DOCKER-USER -i eth0 ! -s 192.168.0.0/16 -j DROP
   sudo apt install iptables-persistent
   ```

> ⚠️ Without this rule, Docker containers may expose ports directly to the internet even if UFW is active!

## SSH Hardening

```bash
sudo sed -i 's/#PasswordAuthentication yes/PasswordAuthentication no/' /etc/ssh/sshd_config
sudo sed -i 's/#PermitRootLogin yes/PermitRootLogin no/' /etc/ssh/sshd_config
sudo systemctl restart sshd
```

## Fail2ban & Unattended Upgrades

```bash
sudo apt install fail2ban unattended-upgrades
sudo dpkg-reconfigure -plow unattended-upgrades
```
