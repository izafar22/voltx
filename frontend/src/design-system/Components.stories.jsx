import React from "react";
import { Link } from "react-router-dom";
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Logo } from "../components/Logo";
import { ThemeToggle } from "../components/ThemeToggle";
export default {
  title: "Components/Shared",
  parameters: {
    docs: {
      description: {
        component:
          "Existing application primitives rendered with shared semantic tokens. All data is illustrative; navigation stays in MemoryRouter and no API provider is mounted.",
      },
    },
  },
};
export const RepairCard = {
  render: () => (
    <Card className="max-w-md">
      <CardHeader>
        <CardTitle>
          <h2 className="font-display text-2xl">Your repair enquiry</h2>
        </CardTitle>
        <CardDescription>Illustrative equipment · RX-DEMO-001</CardDescription>
      </CardHeader>
      <CardContent>
        <p>Technical assessment comes before acceptance and a quotation.</p>
      </CardContent>
      <CardFooter>
        <Button>View assessment</Button>
      </CardFooter>
    </Card>
  ),
};
export const Badges = {
  render: () => (
    <div className="ds-row">
      {["default", "secondary", "outline", "destructive"].map((variant) => (
        <Badge key={variant} variant={variant}>
          {variant}
        </Badge>
      ))}
    </div>
  ),
};
export const Navigation = {
  render: () => (
    <nav className="ds-nav" aria-label="Example navigation">
      <Link to="/" aria-label="RushX home">
        <Logo />
      </Link>
      <Link to="/services" aria-current="page">
        Services
      </Link>
      <Link to="/repairs">Track a repair</Link>
      <ThemeToggle />
      <Button asChild variant="outline">
        <Link to="/login">Sign in</Link>
      </Button>
    </nav>
  ),
};
export const ThemeSwitch = {
  render: () => (
    <div className="ds-stack">
      <h1 className="ds-heading">One theme, every surface</h1>
      <p className="ds-copy">
        The toolbar and this control both use the application ThemeProvider.
        Preference is persisted using rushx-theme.
      </p>
      <ThemeToggle />
    </div>
  ),
};
