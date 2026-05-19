import { readFile, readdir } from "node:fs/promises";
import path from "node:path";
import matter from "gray-matter";
import { remark } from "remark";
import html from "remark-html";

export interface BlogPostFrontmatter {
  title: string;
  slug: string;
  description: string;
  keyword: string;
  product_slug: string;
  published_at: string;
  content_type: string;
}

export interface BlogPost {
  frontmatter: BlogPostFrontmatter;
  contentMarkdown: string;
}

const DEFAULT_BLOG_DIR = path.join(process.cwd(), "..", "state", "blog", "posts");

export async function listBlogPosts(dir = DEFAULT_BLOG_DIR): Promise<BlogPost[]> {
  let entries;
  try {
    entries = await readdir(dir);
  } catch {
    return [];
  }
  const posts: BlogPost[] = [];
  for (const name of entries) {
    if (!name.endsWith(".md")) continue;
    const raw = await readFile(path.join(dir, name), "utf8");
    const parsed = matter(raw);
    posts.push({
      frontmatter: parsed.data as BlogPostFrontmatter,
      contentMarkdown: parsed.content,
    });
  }
  posts.sort((a, b) =>
    b.frontmatter.published_at.localeCompare(a.frontmatter.published_at)
  );
  return posts;
}

export async function getBlogPost(slug: string, dir = DEFAULT_BLOG_DIR): Promise<BlogPost | null> {
  const posts = await listBlogPosts(dir);
  return posts.find((p) => p.frontmatter.slug === slug) ?? null;
}

export async function renderMarkdown(md: string): Promise<string> {
  const processed = await remark().use(html).process(md);
  return processed.toString();
}
