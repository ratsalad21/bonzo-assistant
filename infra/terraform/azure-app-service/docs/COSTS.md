# Azure App Service Cost Notes

This file is a rough cost guide for the Terraform stack in this folder.

It is meant for quick decision-making while learning, not a billing guarantee.
Always verify current prices in the Azure pricing calculator before creating a
long-lived environment.

## Current Dev Shape

The current low-cost dev posture in this repo is:

- App Service Plan: `B1`
- Azure Container Registry: `Basic`
- Azure App Configuration: `developer`
- Key Vault: `standard`
- Terraform state storage: small Azure Storage account + blob container
- App mode: `mock_mode = true`

## Rough Monthly Estimate

For a quiet dev environment running continuously, a practical estimate is:

- around `$20-$30/month`

The main contributors are:

- App Service Plan `B1`
  - biggest cost in this stack
- Azure Container Registry `Basic`
  - low single-digit monthly cost in many regions
- Azure App Configuration `developer`
  - small base cost for non-production use
- Key Vault + Terraform state storage
  - usually negligible at low usage

## What Does Not Add Cost Here

- Requesting Azure quota increases by itself should not add cost
- `mock_mode = true` means no OpenAI API usage charges from this app setup

## What Starts Billing

You start paying when the billable resources actually exist, especially:

- the App Service plan
- the Azure Container Registry
- the App Configuration store

## Cost Control Tips

- Use this stack only for environments you actively need
- Delete the resource group when you are done learning
- Keep `mock_mode = true` until you intentionally want real OpenAI traffic
- Prefer `developer` App Configuration for dev instead of `standard`

## Notes

- Prices vary by region and can change over time
- This repo originally tried `eastus`, then moved to `eastus2` after quota issues
- If your subscription cannot create Basic App Service plans, the stack may need
  a different hosting target such as Azure Container Apps
