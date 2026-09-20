import { Bluetooth, Cloud, Globe, Network, Plug, Server, Smartphone } from "lucide-react";
import type { TargetType } from "@/types/dashboard";

export const TARGET_TYPE_ICON: Record<TargetType, typeof Globe> = {
  web_application: Globe,
  api: Plug,
  server: Server,
  cloud_resource: Cloud,
  mobile_device: Smartphone,
  wireless_device: Bluetooth,
  network_asset: Network,
};

export const TARGET_TYPE_LABEL: Record<TargetType, string> = {
  web_application: "Web Application",
  api: "API",
  server: "Server",
  cloud_resource: "Cloud Resource",
  mobile_device: "Mobile Device",
  wireless_device: "Wireless Device",
  network_asset: "Network Asset",
};
