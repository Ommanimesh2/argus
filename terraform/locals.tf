# =============================================================================
# ARGUS — Locals (Tags & User-Data Scripts)
# =============================================================================

locals {
  common_tags = {
    AuditDemo   = var.audit_demo_tag
    Project     = var.project_name
    Environment = "demo"
    ManagedBy   = "terraform"
  }

  # ---------------------------------------------------------------------------
  # HA-002: Flask app binding on 0.0.0.0 (should bind 127.0.0.1)
  # ---------------------------------------------------------------------------
  ec2_public_user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update && apt-get install -y python3-pip awscli
    pip3 install flask

    mkdir -p /opt/app
    cat > /opt/app/app.py << 'PYEOF'
    from flask import Flask
    app = Flask(__name__)

    @app.route('/health')
    def health():
        return 'ok'

    if __name__ == '__main__':
        # HA-002: Binding on 0.0.0.0 instead of 127.0.0.1
        app.run(host='0.0.0.0', port=8080, debug=True)
    PYEOF

    nohup python3 /opt/app/app.py &
    echo "Flask app started on 0.0.0.0:8080 (HA-002)"
  EOF

  # ---------------------------------------------------------------------------
  # HA-017: Cron job that temporarily opens SSH inbound on ec2-private SG
  # ---------------------------------------------------------------------------
  ec2_private_user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update && apt-get install -y awscli

    cat > /usr/local/bin/allow-ssh-temporarily.sh << 'BASHEOF'
    #!/bin/bash
    SG_ID="$${sg_id}"

    aws ec2 authorize-security-group-ingress \
      --region $${region} \
      --group-id "$SG_ID" \
      --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true

    sleep 300

    aws ec2 revoke-security-group-ingress \
      --region $${region} \
      --group-id "$SG_ID" \
      --protocol tcp --port 22 --cidr 0.0.0.0/0 2>/dev/null || true
    BASHEOF

    chmod +x /usr/local/bin/allow-ssh-temporarily.sh
    echo "0 * * * * /usr/local/bin/allow-ssh-temporarily.sh" | crontab -
    echo "Temporary SSH cron configured (HA-017)"
  EOF

  # ---------------------------------------------------------------------------
  # Jump box user-data: iptables hardening + audit-agent user
  # ---------------------------------------------------------------------------
  jumpbox_user_data = <<-EOF
    #!/bin/bash
    set -e
    apt-get update && apt-get install -y awscli nmap curl openssl iptables-persistent

    # Create audit-agent user (read-only, no sudo)
    useradd -m -s /bin/bash -u 1001 audit-agent
    mkdir -p /home/audit-agent/.ssh
    chmod 700 /home/audit-agent/.ssh

    # iptables hardening
    iptables -F
    iptables -P INPUT DROP
    iptables -P FORWARD DROP
    iptables -P OUTPUT DROP

    # INPUT: SSH from agent server only + established
    iptables -A INPUT -s $${agent_ip} -p tcp --dport 22 -j ACCEPT
    iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    # OUTPUT: SSH to private subnet + AWS APIs + VPC DNS
    iptables -A OUTPUT -d 10.0.10.0/24 -p tcp --dport 22 -j ACCEPT
    iptables -A OUTPUT -d 169.254.169.254/32 -j DROP
    iptables -A OUTPUT -d 169.254.0.0/16 -j DROP
    iptables -A OUTPUT -p tcp --dport 443 -j ACCEPT
    iptables -A OUTPUT -p tcp --dport 53 -d 10.0.0.2/32 -j ACCEPT
    iptables -A OUTPUT -p udp --dport 53 -d 10.0.0.2/32 -j ACCEPT
    iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

    netfilter-persistent save
    echo "Jump box hardened"
  EOF
}
