# Contributing

Thanks for helping improve Vehicle Maintenance Index. Small, focused contributions are welcome.

## Contribution steps

1. **Fork** this repository on GitHub.
2. **Clone** your fork and enter the project folder:

   ```bash
   git clone https://github.com/YOUR-USERNAME/vehicle-maintenance-index.git
   cd vehicle-maintenance-index
   ```

3. **Create a branch** for your change:

   ```bash
   git switch -c your-change-name
   ```

4. **Make your change.** Keep it focused, explain any new setup, and avoid committing secrets such as `.env` files.
5. **Test** the part you changed. For the frontend, run `npm run build` from `frontend`. For the API, follow the setup in the README and check the relevant endpoints in `/docs`.
6. **Commit** your work with a clear message:

   ```bash
   git add .
   git commit -m "Describe your change"
   ```

7. **Push** your branch to your fork:

   ```bash
   git push -u origin your-change-name
   ```

8. **Open a Pull Request** from your branch to this repository. Describe what changed and how you checked it. Link a related issue if there is one.

Please be kind and constructive in reviews. If you are unsure about an idea, open an issue before spending a lot of time on it.
