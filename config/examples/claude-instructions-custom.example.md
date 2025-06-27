# Custom Claude Instructions for Your Project

This file allows you to customize the instructions given to Claude Bot for your specific project. Copy this file to `claude-instructions-custom.md` and modify as needed.

The custom instructions will be appended to the default Claude instructions, allowing you to add project-specific guidance.

## Project-Specific Guidelines

### Code Style and Conventions
```markdown
- Use 2-space indentation for JavaScript/TypeScript
- Follow the Airbnb style guide for React components
- Use camelCase for variables and functions
- Use PascalCase for component names
- Prefer arrow functions for callbacks
```

### Architecture Patterns
```markdown
- Follow the repository pattern for data access
- Use dependency injection for service classes
- Implement the SOLID principles
- Use async/await instead of Promises.then()
- Keep components under 200 lines when possible
```

### Testing Requirements
```markdown
- Write unit tests for all business logic functions
- Use React Testing Library for component tests
- Aim for at least 80% code coverage
- Mock external API calls in tests
- Test error conditions and edge cases
```

### Documentation Standards
```markdown
- Add JSDoc comments to all public functions
- Update the CHANGELOG.md for user-facing changes
- Include examples in API documentation
- Document any environment variables in README
```

### Security Considerations
```markdown
- Validate all user inputs on both client and server
- Use HTTPS for all API communications
- Sanitize data before database operations
- Never log sensitive information
- Use environment variables for secrets
```

### Performance Guidelines
```markdown
- Optimize images and assets for web delivery
- Use lazy loading for large components
- Implement pagination for large data sets
- Cache frequently accessed data appropriately
- Monitor and optimize database queries
```

### Git and Deployment
```markdown
- Follow conventional commit message format
- Create feature branches from main
- Ensure all tests pass before merging
- Update version numbers according to semver
- Include migration scripts for database changes
```

## Technology-Specific Instructions

### React/Next.js Projects
```markdown
- Use functional components with hooks
- Implement proper error boundaries
- Use Next.js Image component for optimized images
- Follow the Next.js file-based routing conventions
- Use TypeScript for all new components
```

### Node.js/Express Projects
```markdown
- Use middleware for cross-cutting concerns
- Implement proper error handling middleware
- Use Helmet.js for security headers
- Follow REST API conventions for endpoints
- Implement request validation with Joi or similar
```

### Database Guidelines
```markdown
- Use transactions for multi-table operations
- Implement proper indexing for query performance
- Use prepared statements to prevent SQL injection
- Follow database naming conventions
- Include data migration scripts
```

## Issue-Specific Instructions

### Bug Fixes
```markdown
- Always reproduce the bug before fixing
- Add regression tests to prevent future occurrences
- Check for similar bugs in related code
- Verify the fix doesn't break existing functionality
- Update any affected documentation
```

### New Features
```markdown
- Break large features into smaller, reviewable commits
- Add comprehensive tests for new functionality
- Update user documentation and examples
- Consider backward compatibility implications
- Add feature flags for gradual rollout if appropriate
```

### Refactoring Tasks
```markdown
- Maintain exact existing functionality
- Refactor in small, focused steps
- Add tests before refactoring if missing
- Update related documentation
- Verify performance isn't negatively impacted
```

## Review and Quality Checklist

Before completing any task, ensure:
- [ ] Code follows project-specific conventions above
- [ ] All tests pass and new tests are added
- [ ] Documentation is updated appropriately
- [ ] Security best practices are followed
- [ ] Performance implications are considered
- [ ] Code is ready for production deployment

## Custom Commands and Scripts

Include any project-specific commands Claude should know about:

```bash
# Run the full test suite
npm run test:full

# Run linting and formatting
npm run lint:fix

# Build for production
npm run build:prod

# Run database migrations
npm run db:migrate

# Start development server with hot reload
npm run dev:watch
```

## Additional Resources

- [Project Wiki](https://github.com/yourorg/yourproject/wiki)
- [API Documentation](https://api.yourproject.com/docs)
- [Design System](https://design.yourproject.com)
- [Contributing Guidelines](./CONTRIBUTING.md)