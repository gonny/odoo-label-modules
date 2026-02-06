# Example Label Module

## Overview

This is an example module demonstrating best practices for Odoo 19 label management modules.

## Features

- **Label Management**: Create, edit, and manage product labels
- **Multiple Label Types**: Support for QR codes, barcodes, and text labels
- **Various Sizes**: Small, medium, and large label sizes
- **State Workflow**: Draft → Confirmed → Printed
- **Product Integration**: Direct integration with Odoo products
- **Access Control**: Role-based permissions for users and managers

## Installation

1. Copy this module to your Odoo addons directory
2. Update the apps list: Settings → Apps → Update Apps List
3. Search for "Example Label Module"
4. Click "Install"

## Configuration

No additional configuration required. The module is ready to use after installation.

## Usage

### Creating a Label

1. Go to Labels → Labels
2. Click "Create"
3. Fill in the label details:
   - Name: Label name
   - Product: Select a product
   - Label Type: Choose QR, Barcode, or Text
   - Size: Select label size
   - Quantity: Number of labels to print
4. Click "Save"

### Label Workflow

1. **Draft**: Initial state when creating a label
2. **Confirmed**: Click "Confirm" to prepare for printing
3. **Printed**: Click "Print" to mark as printed

### Archiving Labels

Click the archive button in the top-right corner to archive a label without deleting it.

## Technical Details

### Models

- `label.label`: Main label model with fields for product, type, size, and state

### Views

- Form view with header buttons and notebook
- Tree view with state decoration
- Kanban view for visual management
- Search view with filters and grouping

### Security

- Users: Read, write, and create permissions
- Stock Managers: Full permissions including delete

## Development

See the module code for examples of:
- Model definitions with various field types
- Computed fields and constraints
- Onchange methods
- Action buttons and workflows
- XML views (form, tree, kanban, search)
- Access control configuration
- Unit tests

## Dependencies

- base
- stock

## License

LGPL-3

## Author

Your Company

## Support

For issues and questions, contact your system administrator.
