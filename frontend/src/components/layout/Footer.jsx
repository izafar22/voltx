import { Link } from "react-router-dom";
import { Zap, MapPin, Mail, Phone } from "lucide-react";

export const Footer = () => (
  <footer className="border-t border-border bg-secondary/40" data-testid="footer">
    <div className="max-w-7xl mx-auto px-5 lg:px-8 py-14 grid gap-10 md:grid-cols-4">
      <div className="space-y-3">
        <div className="flex items-center gap-2">
          <div className="h-9 w-9 rounded-xl bg-primary flex items-center justify-center">
            <Zap className="h-5 w-5 text-white" fill="white" />
          </div>
          <span className="font-display font-extrabold text-xl">RUSHX</span>
        </div>
        <p className="text-sm text-muted-foreground max-w-xs">India's trusted EV charging, energy storage and solar solutions partner — engineered for Indian conditions.</p>
      </div>
      <div>
        <h4 className="font-semibold mb-3 text-sm uppercase tracking-widest text-muted-foreground">Products</h4>
        <ul className="space-y-2 text-sm">
          <li><Link to="/products" className="hover:text-primary transition-colors duration-200">EV Chargers</Link></li>
          <li><Link to="/products/powerboy-powerwall" className="hover:text-primary transition-colors duration-200">PowerBoy Powerwall</Link></li>
          <li><Link to="/products/hearth-solar-inverter" className="hover:text-primary transition-colors duration-200">Hearth Solar Inverter</Link></li>
        </ul>
      </div>
      <div>
        <h4 className="font-semibold mb-3 text-sm uppercase tracking-widest text-muted-foreground">Company</h4>
        <ul className="space-y-2 text-sm">
          <li><Link to="/services" className="hover:text-primary transition-colors duration-200">Services</Link></li>
          <li><Link to="/why-rushx" className="hover:text-primary transition-colors duration-200">Why RUSHX</Link></li>
          <li><Link to="/contact" className="hover:text-primary transition-colors duration-200">Contact</Link></li>
        </ul>
      </div>
      <div>
        <h4 className="font-semibold mb-3 text-sm uppercase tracking-widest text-muted-foreground">Reach us</h4>
        <ul className="space-y-2 text-sm text-muted-foreground">
          <li className="flex items-center gap-2"><MapPin className="h-4 w-4 text-primary" /> Pune, Maharashtra</li>
          <li className="flex items-center gap-2"><Phone className="h-4 w-4 text-primary" /> +91 98765 43210</li>
          <li className="flex items-center gap-2"><Mail className="h-4 w-4 text-primary" /> hello@rushx.in</li>
        </ul>
      </div>
    </div>
    <div className="border-t border-border py-5 text-center text-sm text-muted-foreground">
      © {new Date().getFullYear()} RUSHX Energy Solutions. All rights reserved.
    </div>
  </footer>
);
