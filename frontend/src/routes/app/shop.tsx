import { useState, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import {
  AlertCircle,
  Edit,
  Save,
  X,
  Star,
  Users,
  Calendar,
  CheckCircle,
  Loader2,
  Plus,
  Trash2,
} from "lucide-react"

interface PortfolioItem {
  id: number
  project_name: string
  description: string
  image_url: string
  project_url: string
}

interface ShopData {
  exists: boolean
  id?: number
  company_name?: string
  description?: string
  services_offered?: string
  website?: string
  contact_email?: string
  contact_phone?: string
  years_in_business?: number
  team_size?: number
  subscription_status?: string
  subscription_tier?: string
  subscription_expires?: string
  portfolio?: PortfolioItem[]
  average_rating?: number
  feedback_count?: number
}

export default function BidderShop() {
  const [shop, setShop] = useState<ShopData | null>(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")
  const [formData, setFormData] = useState({
    company_name: "",
    description: "",
    services_offered: "",
    website: "",
    contact_email: "",
    contact_phone: "",
    years_in_business: "",
    team_size: "",
  })

  useEffect(() => {
    fetchShop()
  }, [])

  const fetchShop = async () => {
    try {
      const response = await fetch("/api/v1/bidder/shop")
      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to load shop")
      }

      setShop(data)
      
      if (data.exists) {
        setFormData({
          company_name: data.company_name || "",
          description: data.description || "",
          services_offered: data.services_offered || "",
          website: data.website || "",
          contact_email: data.contact_email || "",
          contact_phone: data.contact_phone || "",
          years_in_business: data.years_in_business?.toString() || "",
          team_size: data.team_size?.toString() || "",
        })
      } else {
        setEditing(true) // Auto-enter edit mode for first-time setup
      }
    } catch (err: any) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    if (!formData.company_name.trim()) {
      setError("Company name is required")
      return
    }

    setSaving(true)
    setError("")

    try {
      const response = await fetch("/api/v1/bidder/shop", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          company_name: formData.company_name,
          description: formData.description || null,
          services_offered: formData.services_offered || null,
          website: formData.website || null,
          contact_email: formData.contact_email || null,
          contact_phone: formData.contact_phone || null,
          years_in_business: formData.years_in_business
            ? parseInt(formData.years_in_business)
            : null,
          team_size: formData.team_size ? parseInt(formData.team_size) : null,
        }),
      })

      const data = await response.json()

      if (!response.ok) {
        throw new Error(data.detail || "Failed to save shop")
      }

      setEditing(false)
      await fetchShop() // Refresh data
    } catch (err: any) {
      setError(err.message)
    } finally {
      setSaving(false)
    }
  }

  const handleCancel = () => {
    if (shop?.exists) {
      // Restore original values
      setFormData({
        company_name: shop.company_name || "",
        description: shop.description || "",
        services_offered: shop.services_offered || "",
        website: shop.website || "",
        contact_email: shop.contact_email || "",
        contact_phone: shop.contact_phone || "",
        years_in_business: shop.years_in_business?.toString() || "",
        team_size: shop.team_size?.toString() || "",
      })
      setEditing(false)
      setError("")
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-5xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-4xl font-bold mb-2">My Shop</h1>
          <p className="text-muted-foreground">
            Manage your bidder profile and portfolio
          </p>
        </div>
        {shop?.exists && !editing && (
          <Button onClick={() => setEditing(true)}>
            <Edit className="h-4 w-4 mr-2" />
            Edit Profile
          </Button>
        )}
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          <AlertCircle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Subscription Status */}
      {shop?.exists && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle>Subscription Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                {shop.subscription_status === "active" ? (
                  <>
                    <CheckCircle className="h-5 w-5 text-green-500" />
                    <div>
                      <p className="font-semibold">Active</p>
                      <p className="text-sm text-muted-foreground">
                        {shop.subscription_tier} plan
                        {shop.subscription_expires &&
                          ` • Expires ${new Date(
                            shop.subscription_expires
                          ).toLocaleDateString()}`}
                      </p>
                    </div>
                  </>
                ) : (
                  <>
                    <AlertCircle className="h-5 w-5 text-orange-500" />
                    <div>
                      <p className="font-semibold">Inactive</p>
                      <p className="text-sm text-muted-foreground">
                        Subscribe to access marketplace requests
                      </p>
                    </div>
                  </>
                )}
              </div>
              <Button variant="outline">Manage Subscription</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Shop Profile */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle>Company Profile</CardTitle>
          <CardDescription>
            Your profile is visible to clients in the marketplace
          </CardDescription>
        </CardHeader>
        <CardContent>
          {editing ? (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="company_name">
                  Company Name <span className="text-red-500">*</span>
                </Label>
                <Input
                  id="company_name"
                  value={formData.company_name}
                  onChange={(e) =>
                    setFormData({ ...formData, company_name: e.target.value })
                  }
                  placeholder="Your Company Name"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">About Your Company</Label>
                <Textarea
                  id="description"
                  value={formData.description}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                  placeholder="Tell clients about your expertise..."
                  rows={4}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="services">Services Offered</Label>
                <Textarea
                  id="services"
                  value={formData.services_offered}
                  onChange={(e) =>
                    setFormData({
                      ...formData,
                      services_offered: e.target.value,
                    })
                  }
                  placeholder="List your services (one per line)"
                  rows={3}
                />
              </div>

              <div className="grid md:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="website">Website</Label>
                  <Input
                    id="website"
                    type="url"
                    value={formData.website}
                    onChange={(e) =>
                      setFormData({ ...formData, website: e.target.value })
                    }
                    placeholder="https://yourcompany.com"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="contact_email">Contact Email</Label>
                  <Input
                    id="contact_email"
                    type="email"
                    value={formData.contact_email}
                    onChange={(e) =>
                      setFormData({ ...formData, contact_email: e.target.value })
                    }
                    placeholder="contact@yourcompany.com"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="contact_phone">Contact Phone</Label>
                  <Input
                    id="contact_phone"
                    value={formData.contact_phone}
                    onChange={(e) =>
                      setFormData({ ...formData, contact_phone: e.target.value })
                    }
                    placeholder="+1 (555) 123-4567"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="years">Years in Business</Label>
                  <Input
                    id="years"
                    type="number"
                    value={formData.years_in_business}
                    onChange={(e) =>
                      setFormData({
                        ...formData,
                        years_in_business: e.target.value,
                      })
                    }
                    placeholder="5"
                  />
                </div>

                <div className="space-y-2">
                  <Label htmlFor="team_size">Team Size</Label>
                  <Input
                    id="team_size"
                    type="number"
                    value={formData.team_size}
                    onChange={(e) =>
                      setFormData({ ...formData, team_size: e.target.value })
                    }
                    placeholder="10"
                  />
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <Button onClick={handleSave} disabled={saving}>
                  {saving ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Saving...
                    </>
                  ) : (
                    <>
                      <Save className="h-4 w-4 mr-2" />
                      Save Profile
                    </>
                  )}
                </Button>
                {shop?.exists && (
                  <Button variant="outline" onClick={handleCancel}>
                    <X className="h-4 w-4 mr-2" />
                    Cancel
                  </Button>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <div>
                <h3 className="font-semibold text-2xl mb-1">
                  {shop?.company_name}
                </h3>
                {shop?.description && (
                  <p className="text-muted-foreground whitespace-pre-wrap">
                    {shop.description}
                  </p>
                )}
              </div>

              {shop?.services_offered && (
                <div>
                  <h4 className="font-semibold mb-2">Services Offered</h4>
                  <p className="text-muted-foreground whitespace-pre-wrap">
                    {shop.services_offered}
                  </p>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-4 pt-4">
                {shop?.website && (
                  <div>
                    <p className="text-sm font-medium">Website</p>
                    <a
                      href={shop.website}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sm text-primary hover:underline"
                    >
                      {shop.website}
                    </a>
                  </div>
                )}

                {shop?.contact_email && (
                  <div>
                    <p className="text-sm font-medium">Email</p>
                    <p className="text-sm text-muted-foreground">
                      {shop.contact_email}
                    </p>
                  </div>
                )}

                {shop?.years_in_business && (
                  <div className="flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">
                      {shop.years_in_business} years in business
                    </span>
                  </div>
                )}

                {shop?.team_size && (
                  <div className="flex items-center gap-2">
                    <Users className="h-4 w-4 text-muted-foreground" />
                    <span className="text-sm">{shop.team_size} team members</span>
                  </div>
                )}

                {shop?.average_rating && (
                  <div className="flex items-center gap-2">
                    <Star className="h-4 w-4 text-yellow-500" />
                    <span className="text-sm">
                      {shop.average_rating.toFixed(1)} ({shop.feedback_count}{" "}
                      reviews)
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Portfolio */}
      {shop?.exists && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Portfolio</CardTitle>
                <CardDescription>Showcase your past projects</CardDescription>
              </div>
              <Button size="sm">
                <Plus className="h-4 w-4 mr-2" />
                Add Project
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {!shop.portfolio || shop.portfolio.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <p>No portfolio items yet</p>
                <p className="text-sm">Add projects to showcase your work</p>
              </div>
            ) : (
              <div className="grid md:grid-cols-2 gap-4">
                {shop.portfolio.map((item) => (
                  <Card key={item.id}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between mb-2">
                        <h4 className="font-semibold">{item.project_name}</h4>
                        <Button size="sm" variant="ghost">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                      {item.description && (
                        <p className="text-sm text-muted-foreground mb-2">
                          {item.description}
                        </p>
                      )}
                      {item.project_url && (
                        <a
                          href={item.project_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-sm text-primary hover:underline"
                        >
                          View Project →
                        </a>
                      )}
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}
