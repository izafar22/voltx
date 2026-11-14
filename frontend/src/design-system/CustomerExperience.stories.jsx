import React from "react";
import { Home, Wrench } from "lucide-react";
import { LoginLayout } from "../components/layout/LoginLayout";
import { SidebarLinks } from "../components/layout/SidebarLinks";
import { RepairCTA, EmptyState } from "../components/patterns/CustomerPatterns";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { RepairStatus } from "../components/patterns/RepairStatus";
import "../pages/customer/CustomerHome.css";
export default {
  title: "Patterns/Customer Experience",
  parameters: {
    docs: {
      description: {
        component:
          "Shared production presentation with synthetic content only. Authentication handlers and APIs stay in the app; stories have no auth provider or network calls.",
      },
    },
  },
};
export const Login = {
  render: () => (
    <LoginLayout>
      <div>
        <h1 className="font-display text-3xl font-medium">Sign in</h1>
        <p className="text-muted-foreground mt-2">
          Enter your phone number to continue.
        </p>
      </div>
      <div>
        <label htmlFor="story-phone">Phone number</label>
        <Input
          id="story-phone"
          type="tel"
          autoComplete="tel"
          className="mt-2"
        />
      </div>
      <Button disabled className="w-full">
        Send OTP
      </Button>
      <Button variant="outline" className="w-full">
        Continue with Google
      </Button>
      <p className="text-sm text-muted-foreground">
        Illustrative layout; sign-in is disabled in Storybook.
      </p>
    </LoginLayout>
  ),
};
export const Sidebar = {
  render: () => (
    <aside className="max-w-xs border border-border rounded-lg">
      <SidebarLinks
        items={[
          { to: "/app", label: "Home", icon: Home },
          { to: "/repairs", label: "Repairs", icon: Wrench },
        ]}
      />
    </aside>
  ),
};
export const Empty = {
  render: () => (
    <EmptyState
      title="No repair requests yet"
      description="Start with an assessment. Your requests and status updates will appear here."
    />
  ),
};
export const CTA = { render: () => <RepairCTA onRequest={() => {}} /> };
export const Dashboard = {
  render: () => (
    <div className="customer-dashboard">
      <div>
        <p className="text-muted-foreground">Welcome back</p>
        <h1 className="font-display text-3xl font-semibold">
          Illustrative Customer
        </h1>
      </div>
      <RepairCTA onRequest={() => {}} />
      <EmptyState
        title="No repair requests yet"
        description="Your requests and status updates will appear here."
      />
      <div>
        <h2 className="font-display text-xl mb-3">Example status</h2>
        <RepairStatus status="DIAGNOSING" />
      </div>
    </div>
  ),
};
