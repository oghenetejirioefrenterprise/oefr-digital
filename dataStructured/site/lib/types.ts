export type ComplianceVerdict = "PASS" | "FAIL" | "NEEDS_FOUNDER_REVIEW";

export type LaunchStatus =
  | "FULLY_SHIPPED"
  | "PARTIAL_SHIPPED"
  | "DRAFT"
  | "FAILED";

export interface ProductSpec {
  version: number;
  type: "product_spec";
  slug: string;
  created: string;
  created_by: string;
  status: string;
  name: string;
  summary: string;
  format: string;
  deliverable: string;
  price_usd: number;
  bonus_stack: string[];
  dataset_file: string;
  ethics_ledger: string;
  audience: string;
  stripe_product_prefix: string;
  channels: string[];
  compliance_verdict: ComplianceVerdict;
  compliance_audited_at: string;
  row_count: number;
  source: string;
  gumroad_listing?: {
    title: string;
    description: string;
    price: number;
    [k: string]: unknown;
  };
}

export interface LaunchReport {
  version: number;
  type: "launch_report";
  slug: string;
  created: string;
  created_by: string;
  status: LaunchStatus;
  summary: string;
  stripe_product_id: string;
  stripe_price_id: string;
  stripe_payment_link_url: string;
  smoke_test: {
    passed: boolean;
    checked_at: string;
  };
  spec_file: string;
  gumroad_listing_url?: string;
  gumroad_product_id?: string;
  gumroad_deployed_at?: string;
}

export interface Product {
  slug: string;
  spec: ProductSpec;
  launch: LaunchReport;
}
